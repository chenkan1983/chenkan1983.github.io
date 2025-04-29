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
    # 中文数字映射表
    cn_num = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000, '万': 10000
    }
    
    # 从章节名称中提取数字（支持阿拉伯数字和中文数字）
    # 严格匹配"第x章"格式，确保章节号前后没有其他数字或中文数字
    arabic_match = re.search(r'^第(\d+)章(?![零一二三四五六七八九十百千万\d])[^零一二三四五六七八九十百千万\d]*', chapter_text)
    if arabic_match:
        num = int(arabic_match.group(1))
        print(f"提取到阿拉伯数字章节号: {chapter_text} -> {num}")
        return num
    
    chinese_match = re.search(r'^第([零一二三四五六七八九十百千万]+)章(?![零一二三四五六七八九十百千万\d])[^零一二三四五六七八九十百千万\d]*', chapter_text)
    if chinese_match:
        cn_str = chinese_match.group(1)
        
        # 处理中文数字
        result = 0
        temp_num = 0
        unit = 1
        
        # 从左向右处理每个字符
        for i, char in enumerate(cn_str):
            if char in ['百', '千', '万']:
                # 如果前面没有数字，默认为1
                if temp_num == 0:
                    temp_num = 1
                if char == '万':
                    result += temp_num * 10000
                elif char == '千':
                    result += temp_num * 1000
                elif char == '百':
                    result += temp_num * 100
                temp_num = 0
            elif char == '十':
                # 处理"十"的特殊情况
                if i == 0:  # 如果"十"在开头
                    temp_num = 1
                if temp_num == 0:
                    temp_num = 1
                result += temp_num * 10
                temp_num = 0
            else:
                temp_num = cn_num[char]
        
        # 处理最后的数字
        if temp_num > 0:
            result += temp_num
        
        print(f"提取到中文数字章节号: {chapter_text} -> {result}")
        return result
    
    print(f"无法提取章节号: {chapter_text}")
    return 0  # 如果没有找到有效的章节号，返回0

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
            
            # 验证章节标题格式
            if not re.search(r'^第[零一二三四五六七八九十百千万\d]+章', title):
                print(f"跳过非标准章节: {title}")
                return None, None
            
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
                
                # 如果获取成功且是有效的章节标题，直接写入文件
                if chapter_title and chapter_content and re.search(r'^第[零一二三四五六七八九十百千万\d]+章', chapter_title):
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
        self.root.geometry('800x700')  # 增加窗口高度
        
        # 设置整体样式
        style = ttk.Style()
        style.configure('TFrame', padding=20)
        style.configure('TLabel', font=('微软雅黑', 12))
        style.configure('TEntry', font=('微软雅黑', 12), padding=5)  # 增加输入框内边距
        style.configure('TButton', 
                       font=('微软雅黑', 12, 'bold'), 
                       padding=(20, 10))
        style.configure('TLabelframe', padding=20)  # 增加标签框架内边距
        style.configure('TLabelframe.Label', font=('微软雅黑', 12, 'bold'))
        
        # 创建顶部间距框架
        top_padding = ttk.Frame(root, height=4)
        top_padding.pack(side=tk.TOP, fill=tk.X)
        
        # 创建主框架并居中，使用Canvas和Scrollbar
        canvas = tk.Canvas(root)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        main_frame = ttk.Frame(canvas, padding="4", style='TFrame')
        
        # 配置Canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局滚动组件
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建窗口来包含主框架
        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor="nw", width=canvas.winfo_width())
        
        # URL输入框架
        url_frame = ttk.LabelFrame(main_frame, text="网址设置", padding=15)  # 增加内边距
        url_frame.pack(fill=tk.X, pady=(0, 15))  # 增加外边距
        
        url_content_frame = ttk.Frame(url_frame)
        url_content_frame.pack(fill=tk.X, padx=25, pady=10)  # 增加内边距
        ttk.Label(url_content_frame, text="小说目录URL:").pack(side=tk.LEFT)
        self.url_var = tk.StringVar(value='https://www.5dscw.com/book_94211100/')
        ttk.Entry(url_content_frame, textvariable=self.url_var, width=60).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # 章节设置框架
        chapter_frame = ttk.LabelFrame(main_frame, text="章节设置", padding=15)
        chapter_frame.pack(fill=tk.X, pady=15)
        
        # 起始章节
        start_frame = ttk.Frame(chapter_frame)
        start_frame.pack(fill=tk.X, padx=25, pady=10)
        ttk.Label(start_frame, text="起始章节:").pack(side=tk.LEFT)
        self.start_var = tk.StringVar(value='1')
        ttk.Entry(start_frame, textvariable=self.start_var, width=10).pack(side=tk.LEFT, padx=10)
        
        # 结束章节
        end_frame = ttk.Frame(chapter_frame)
        end_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(end_frame, text="结束章节:").pack(side=tk.LEFT)
        self.end_var = tk.StringVar()
        ttk.Entry(end_frame, textvariable=self.end_var, width=10).pack(side=tk.LEFT, padx=10)
        ttk.Label(end_frame, text="(留空表示爬取到最后)").pack(side=tk.LEFT)
        
        # 线程设置框架
        thread_frame = ttk.LabelFrame(main_frame, text="性能设置", padding=10)
        thread_frame.pack(fill=tk.X, pady=10)
        
        thread_content_frame = ttk.Frame(thread_frame)
        thread_content_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(thread_content_frame, text="线程数:").pack(side=tk.LEFT)
        self.threads_var = tk.StringVar(value='10')
        ttk.Entry(thread_content_frame, textvariable=self.threads_var, width=10).pack(side=tk.LEFT, padx=10)
        
        # 输出设置框架
        output_frame = ttk.LabelFrame(main_frame, text="输出设置", padding=10)
        output_frame.pack(fill=tk.X, pady=10)
        
        output_content_frame = ttk.Frame(output_frame)
        output_content_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(output_content_frame, text="输出目录:").pack(side=tk.LEFT)
        self.output_var = tk.StringVar(value='novels')
        ttk.Entry(output_content_frame, textvariable=self.output_var, width=50).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # 进度显示框架
        progress_frame = ttk.LabelFrame(main_frame, text="进度", padding=10)
        progress_frame.pack(fill=tk.X, pady=10)
        
        progress_content_frame = ttk.Frame(progress_frame)
        progress_content_frame.pack(fill=tk.X, padx=20, pady=5)
        self.progress_var = tk.StringVar(value='准备就绪')
        progress_label = ttk.Label(progress_content_frame, textvariable=self.progress_var)
        progress_label.pack(fill=tk.X, pady=5)
        
        # 开始按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 20))
        
        # 创建自定义按钮样式
        style = ttk.Style()
        style.configure('BigButton.TButton',
                       font=('微软雅黑', 16, 'bold'),
                       padding=(80, 40),  # 显著增加按钮内边距
                       cursor='hand2')  # 添加手型光标
        
        # 开始按钮容器
        button_container = ttk.Frame(button_frame, padding=20)
        button_container.pack(expand=True)
        
        start_button = ttk.Button(button_container,
                                text="开始爬取",
                                command=self.start_crawling,
                                style='BigButton.TButton')
        start_button.pack(expand=True, ipadx=30, ipady=15)  # 增加内部填充
        
        # 添加鼠标悬停效果
        def on_enter(e):
            e.widget.configure(style='BigButton.TButton.hover')
        
        def on_leave(e):
            e.widget.configure(style='BigButton.TButton')
        
        # 配置悬停样式
        style.configure('BigButton.TButton.hover',
                       font=('微软雅黑', 16, 'bold'),
                       padding=(80, 40),
                       cursor='hand2',
                       background='#e1e1e1')  # 悬停时的背景色
        
        start_button.bind('<Enter>', on_enter)
        start_button.bind('<Leave>', on_leave)
        
        # 配置主框架大小调整
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def configure_canvas_width(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        # 绑定事件
        main_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", configure_canvas_width)
        
        # 配置鼠标滚轮滚动
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # 配置网格权重
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # 创建加载动画窗口
        self.loading_window = None
        self.loading_dots = 0
        self.loading_animation = None
    
    def show_loading(self):
        if self.loading_window is None:
            self.loading_window = tk.Toplevel(self.root)
            self.loading_window.title("准备中")
            self.loading_window.geometry("200x100")
            self.loading_window.transient(self.root)  # 设置为主窗口的子窗口
            self.loading_window.grab_set()  # 模态窗口
            
            # 居中显示
            x = self.root.winfo_x() + (self.root.winfo_width() - 200) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - 100) // 2
            self.loading_window.geometry(f"+{x}+{y}")
            
            # 添加加载文本标签
            self.loading_label = ttk.Label(self.loading_window, text="准备中...")
            self.loading_label.pack(expand=True)
            
            # 开始动画
            self.update_loading_animation()
    
    def update_loading_animation(self):
        if self.loading_window:
            self.loading_dots = (self.loading_dots + 1) % 4
            dots = "." * self.loading_dots
            self.loading_label.config(text=f"准备中{dots}")
            self.loading_animation = self.root.after(500, self.update_loading_animation)
    
    def hide_loading(self):
        if self.loading_window:
            if self.loading_animation:
                self.root.after_cancel(self.loading_animation)
                self.loading_animation = None
            self.loading_window.destroy()
            self.loading_window = None
    
    def start_crawling(self):
        try:
            # 显示加载动画
            self.show_loading()
            
            # 获取输入值
            base_url = self.url_var.get().strip()
            start = int(self.start_var.get())
            end = int(self.end_var.get()) if self.end_var.get().strip() else None
            threads = int(self.threads_var.get())
            output = self.output_var.get().strip()
            
            # 参数验证
            if not base_url:
                self.hide_loading()
                messagebox.showerror("错误", "请输入小说目录URL")
                return
            if start < 1:
                self.hide_loading()
                messagebox.showerror("错误", "起始章节必须大于0")
                return
            if threads < 1:
                self.hide_loading()
                messagebox.showerror("错误", "线程数必须大于0")
                return
            
            # 创建并启动爬取线程
            self.progress_var.set("正在爬取中...")
            threading.Thread(target=self.run_crawler, args=(base_url, start, end, threads, output), daemon=True).start()
            
            # 隐藏加载动画
            self.hide_loading()
            
        except ValueError as e:
            self.hide_loading()
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
            
            # 生成要匹配的章节名称列表并打印
            target_chapters = []
            if end is not None:
                print("\n准备爬取以下章节：")
                for i in range(start, end + 1):
                    chapter_name = f"第{i}章"
                    target_chapters.append(chapter_name)
                    print(f"- {chapter_name}")
                print("\n开始匹配章节...\n")
            
            # 根据章节号筛选
            filtered_chapters = []
            filtered_urls = []
            
            # 创建章节名称到URL的映射
            chapter_map = {}
            for chapter, url in zip(chapters, chapter_urls):
                # 提取章节号
                chapter_num = extract_chapter_number(chapter)
                if chapter_num > 0:  # 确保能提取到有效的章节号
                    # 使用标准格式作为键
                    standard_name = f"第{chapter_num}章"
                    chapter_map[standard_name] = (chapter, url)
            
            # 按照目标章节列表顺序匹配
            if end is not None:
                for target_chapter in target_chapters:
                    if target_chapter in chapter_map:
                        chapter, url = chapter_map[target_chapter]
                        filtered_chapters.append(chapter)
                        filtered_urls.append(url)
                        print(f"目标章节 {target_chapter} -> 匹配到实际章节: {chapter}")
                    else:
                        print(f"未找到目标章节: {target_chapter}")
            else:
                # 如果没有指定结束章节，则获取所有大于等于起始章节的章节
                for chapter, url in sorted(zip(chapters, chapter_urls), 
                                        key=lambda x: extract_chapter_number(x[0])):
                    chapter_num = extract_chapter_number(chapter)
                    if chapter_num >= start:
                        filtered_chapters.append(chapter)
                        filtered_urls.append(url)
                        print(f"匹配到目标章节: {chapter}")
            
            # 验证是否获取到了所有需要的章节
            if end is not None:
                missing_chapters = set(target_chapters) - {f"第{extract_chapter_number(ch)}章" for ch in filtered_chapters}
                if missing_chapters:
                    missing_str = ", ".join(sorted(missing_chapters))
                    self.progress_var.set(f"警告：缺少以下章节：{missing_str}")
                    messagebox.showwarning("警告", f"未找到部分章节：{missing_str}")
                    if not filtered_chapters:
                        return
            
            # 创建任务队列
            task_queue = Queue()
            
            # 将任务添加到队列，并显示实际章节号
            for i, (chapter, chapter_url) in enumerate(zip(filtered_chapters, filtered_urls)):
                chapter_num = extract_chapter_number(chapter)
                print(f"添加任务：第 {chapter_num} 章")
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