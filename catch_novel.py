import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time
import threading
from queue import Queue, Empty
import os
import tkinter as tk
from tkinter import ttk, messagebox
import argparse

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

class NovelCrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title('小说章节爬取工具')
        self.root.geometry('600x400')
        
        # 创建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # URL输入
        ttk.Label(main_frame, text="小说目录URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_var = tk.StringVar(value='https://www.3wwd.com/book_94758315/')
        ttk.Entry(main_frame, textvariable=self.url_var, width=50).grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # 起始章节
        ttk.Label(main_frame, text="起始章节:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.start_var = tk.StringVar(value='1')
        ttk.Entry(main_frame, textvariable=self.start_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 结束章节
        ttk.Label(main_frame, text="结束章节:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.end_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.end_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=5)
        ttk.Label(main_frame, text="(留空表示爬取到最后)").grid(row=2, column=2, sticky=tk.W, pady=5)
        
        # 线程数
        ttk.Label(main_frame, text="线程数:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.threads_var = tk.StringVar(value='10')
        ttk.Entry(main_frame, textvariable=self.threads_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # 输出目录
        ttk.Label(main_frame, text="输出目录:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.output_var = tk.StringVar(value='novels')
        ttk.Entry(main_frame, textvariable=self.output_var, width=50).grid(row=4, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # 进度显示
        self.progress_var = tk.StringVar(value='准备就绪')
        ttk.Label(main_frame, textvariable=self.progress_var).grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=20)
        
        # 开始按钮 - 放大版本
        start_button = ttk.Button(main_frame, text="开始爬取", command=self.start_crawling)
        start_button.grid(row=6, column=0, columnspan=3, pady=20)
        
        # 设置按钮样式
        style = ttk.Style()
        style.configure('TButton', font=('TkDefaultFont', 12, 'bold'))  # 增大字体并加粗
        start_button.configure(style='TButton', padding=(20, 10))  # 增加按钮内边距
    
    def start_crawling(self):
        try:
            # 获取输入值
            base_url = self.url_var.get().strip()
            start = int(self.start_var.get())
            end = int(self.end_var.get()) if self.end_var.get().strip() else None
            threads = int(self.threads_var.get())
            output = self.output_var.get().strip()
            
            # 参数验证
            if not base_url:
                messagebox.showerror("错误", "请输入小说目录URL")
                return
            if start < 1:
                messagebox.showerror("错误", "起始章节必须大于0")
                return
            if threads < 1:
                messagebox.showerror("错误", "线程数必须大于0")
                return
            
            # 创建并启动爬取线程
            self.progress_var.set("正在爬取中...")
            threading.Thread(target=self.run_crawler, args=(base_url, start, end, threads, output), daemon=True).start()
            
        except ValueError as e:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def run_crawler(self, base_url, start, end, threads, output):
        try:
            # 创建novels目录
            if not os.path.exists(output):
                os.makedirs(output)
            
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
            
            # 从URL中提取book_id
            book_id = re.search(r'book_(\d+)', base_url)
            book_id = book_id.group(1) if book_id else ''
            
            for dd in dd_tags:
                # 在 dd 标签中查找链接
                link = dd.find('a')
                if link and f'/book_{book_id}/' in link.get('href', ''):
                    chapter_text = link.text.strip()
                    chapter_url = urljoin(base_url, link.get('href', ''))
                    if chapter_text:
                        chapters.append(chapter_text)
                        chapter_urls.append(chapter_url)
            
            # 按章节号排序
            sorted_chapters = sorted(zip(chapters, chapter_urls), key=lambda x: extract_chapter_number(x[0]))
            chapters, chapter_urls = zip(*sorted_chapters)
            
            # 根据起始和结束章节数筛选
            start_index = max(0, start - 1)  # 修改这里，使用传入的start参数
            end_index = end if end is not None else len(chapters)  # 修改这里，使用传入的end参数
            chapters = chapters[start_index:end_index]
            chapter_urls = chapter_urls[start_index:end_index]
            
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
            for _ in range(threads):  # 修改这里，使用传入的threads参数
                worker = ChapterWorker(task_queue, output, thread_lock)  # 修改这里，使用传入的output参数
                worker.start()
                workers.append(worker)
            
            # 等待所有任务完成
            task_queue.join()
            
            # 停止所有线程
            for _ in range(threads):  # 修改这里，使用传入的threads参数而不是num_threads
                task_queue.put(None)
            
            # 统计完成的章节数
            for worker in workers:
                worker.join()
                total_completed += worker.completed_chapters
            
            self.progress_var.set(f"爬取完成！总共获取了 {total_completed} 个章节")
            messagebox.showinfo("完成", f"所有章节内容已保存到 {output} 目录")
            
        except Exception as e:
            self.progress_var.set(f"发生错误: {str(e)}")
            messagebox.showerror("错误", str(e))

def main():
    root = tk.Tk()
    app = NovelCrawlerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()