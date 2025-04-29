import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time
import threading
from queue import Queue, Empty
import os

def extract_chapter_number(chapter_text):
    # 从章节名称中提取数字
    match = re.search(r'(\d+)章', chapter_text)
    return int(match.group(1)) if match else 0

def get_chapter_content(url):
    # 设置请求头，模拟浏览器访问
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        all_content = []  # 存储所有页面的内容
        current_url = url
        
        while True:
            # 发送GET请求
            response = requests.get(current_url, headers=headers)
            response.encoding = 'utf-8'  # 设置编码
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取章节标题
            title = soup.find('h1').text.strip() if soup.find('h1') else '未知章节'
            
            # 获取内容div
            content_div = soup.find('div', id='content')
            if content_div:
                # 获取div中的所有文本内容，包括直接文本和p标签中的文本
                content_parts = []
                for element in content_div.children:
                    if isinstance(element, str):
                        # 处理直接的文本内容
                        text = element.strip()
                        if text:
                            content_parts.append(text)
                    elif element.name == 'p':
                        # 处理p标签中的文本
                        text = element.text.strip()
                        if text:
                            content_parts.append(text)
                    elif element.name == 'br':
                        # 处理换行标签
                        content_parts.append('')
                
                # 清理内容，移除空行和广告文本
                cleaned_content = []
                for part in content_parts:
                    part = part.strip()
                    # 跳过广告和空内容
                    if part and not any(ad in part.lower() for ad in ['广告', 'http', 'www', '.com', '.cn']):
                        cleaned_content.append(part)
                
                # 合并内容，保持适当的换行
                content = '\n\n'.join(cleaned_content)
                all_content.append(content)
            
            # 查找下一页链接
            next_link = soup.find('a', string=re.compile(r'下一页|下页'))
            if next_link and 'href' in next_link.attrs:
                current_url = urljoin(url, next_link['href'])
                time.sleep(1)  # 添加延时，避免请求过快
            else:
                break
        
        # 合并所有页面的内容
        full_content = '\n\n'.join(all_content)
        return title, full_content
        
    except Exception as e:
        print(f"获取章节内容时出错: {str(e)}")
        return None, None

class ChapterWorker(threading.Thread):
    def __init__(self, queue, novels_dir, lock):
        threading.Thread.__init__(self)
        self.queue = queue
        self.novels_dir = novels_dir
        self.lock = lock
        self.completed_chapters = 0
    
    def run(self):
        while True:
            try:
                # 从队列获取任务
                chapter_info = self.queue.get_nowait()
                if chapter_info is None:
                    break
                
                index, chapter, chapter_url = chapter_info
                print(f"正在获取第 {index+1} 章的内容...")
                
                # 获取章节内容
                chapter_title, chapter_content = get_chapter_content(chapter_url)
                
                # 如果获取成功，直接写入文件
                if chapter_title and chapter_content:
                    with self.lock:
                        save_chapter_to_file(chapter, chapter_content, self.novels_dir)
                        self.completed_chapters += 1
                
                time.sleep(1)  # 稍微降低请求频率
                self.queue.task_done()
                
            except Empty:
                break
            except Exception as e:
                print(f"处理章节时出错: {str(e)}")
                self.queue.task_done()
                break

def save_chapter_to_file(chapter_name, content, novels_dir):
    # 清理文件名中的非法字符
    safe_filename = re.sub(r'[<>:"/\\|?*]', '', chapter_name)
    file_path = os.path.join(novels_dir, f"{safe_filename}.txt")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        # 写入章节标题
        f.write(chapter_name + '\n\n')
        # 写入章节内容
        formatted_paragraphs = ['    ' + p for p in content.split('\n\n')]
        f.write('\n'.join(formatted_paragraphs))

def main():
    base_url = 'https://www.3wwd.com/book_94758315/'
    novels_dir = 'novels'
    num_threads = 10  # 设置线程数
    
    try:
        # 创建novels目录
        if not os.path.exists(novels_dir):
            os.makedirs(novels_dir)
        
        # 获取首页内容
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(base_url, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有的 dd 标签
        dd_tags = soup.find_all('dd')
        chapters = []
        chapter_urls = []
        
        for dd in dd_tags:
            # 在 dd 标签中查找链接
            link = dd.find('a')
            if link and '/book_94758315/' in link.get('href', ''):
                chapter_text = link.text.strip()
                chapter_url = urljoin(base_url, link.get('href', ''))
                if chapter_text:
                    chapters.append(chapter_text)
                    chapter_urls.append(chapter_url)
        
        # 按章节号排序
        sorted_chapters = sorted(zip(chapters, chapter_urls), key=lambda x: extract_chapter_number(x[0]))
        chapters, chapter_urls = zip(*sorted_chapters)
        
        # 删除这两行，不再限制章节数
        # chapters = chapters[:max_chapters]
        # chapter_urls = chapter_urls[:max_chapters]
        
        # 创建任务队列
        task_queue = Queue()
        
        # 将任务添加到队列
        for i, (chapter, chapter_url) in enumerate(zip(chapters, chapter_urls)):
            task_queue.put((i, chapter, chapter_url))
        
        # 创建一个线程锁
        thread_lock = threading.Lock()
        
        # 创建工作线程
        workers = []
        total_completed = 0
        for _ in range(num_threads):
            worker = ChapterWorker(task_queue, novels_dir, thread_lock)
            worker.start()
            workers.append(worker)
        
        # 等待所有任务完成
        task_queue.join()
        
        # 停止所有线程
        for _ in range(num_threads):
            task_queue.put(None)
        
        # 统计完成的章节数
        for worker in workers:
            worker.join()
            total_completed += worker.completed_chapters
        
        print(f"总共获取了 {total_completed} 个章节")
        print(f"所有章节内容已保存到 {novels_dir} 目录")
            
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main()