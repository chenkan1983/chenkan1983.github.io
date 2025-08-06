#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR HTTP API 服务器
提供图片OCR识别和视频数据指标提取的API接口
"""

import os
import sys
import re
import json
import uuid
import threading
import queue
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify
from paddleocr import PaddleOCR
from werkzeug.utils import secure_filename
import traceback

app = Flask(__name__)

# 配置JSON编码，确保中文字符正常显示
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'

# 配置上传目录
UPLOAD_FOLDER = 'ocr_images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传文件大小为16MB

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

# 创建上传目录
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# OCR实例池管理器
class OCRPool:
    """线程安全的OCR实例池"""
    
    def __init__(self, pool_size=4):
        self.pool_size = pool_size
        self.pool = queue.Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self.initialized = False
        
    def initialize(self):
        """初始化OCR实例池"""
        with self.lock:
            if self.initialized:
                return True
                
            try:
                print(f"正在初始化OCR实例池（大小: {self.pool_size}）...")
                for i in range(self.pool_size):
                    print(f"初始化OCR实例 {i+1}/{self.pool_size}...")
                    ocr_instance = PaddleOCR(
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_textline_orientation=False,
                        lang='ch'  # 支持中文
                    )
                    self.pool.put(ocr_instance)
                    
                self.initialized = True
                print("OCR实例池初始化完成！")
                return True
                
            except Exception as e:
                print(f"OCR实例池初始化失败: {e}")
                traceback.print_exc()
                return False
    
    def get_ocr(self, timeout=30):
        """从池中获取OCR实例"""
        if not self.initialized:
            raise RuntimeError("OCR池未初始化")
        try:
            return self.pool.get(timeout=timeout)
        except queue.Empty:
            raise RuntimeError("获取OCR实例超时，请稍后重试")
    
    def return_ocr(self, ocr_instance):
        """将OCR实例返回池中"""
        if self.initialized:
            self.pool.put(ocr_instance)
    
    def get_pool_status(self):
        """获取池状态"""
        return {
            'pool_size': self.pool_size,
            'available': self.pool.qsize(),
            'in_use': self.pool_size - self.pool.qsize(),
            'initialized': self.initialized
        }

# 全局OCR池实例
ocr_pool = OCRPool(pool_size=4)

# 在模块加载时初始化OCR池（适用于Gunicorn等WSGI服务器）
def init_app():
    """应用初始化函数"""
    if not ocr_pool.initialize():
        print("OCR池初始化失败，程序退出")
        sys.exit(1)

def allowed_file(filename):
    """
    检查文件扩展名是否允许
    
    Args:
        filename: 文件名
    
    Returns:
        bool: 是否允许的文件类型
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_video_metrics(texts):
    """
    从OCR识别的文本列表中解析视频数据指标
    
    Args:
        texts: OCR识别出的文本列表
    
    Returns:
        dict: 包含解析出的指标数据
    """
    metrics = {}
    
    if not texts or not isinstance(texts, list):
        return metrics
    
    try:
        # 1. 播放量 - 查找独立的"播放量"字符串，然后在附近查找数字
        for i, text in enumerate(texts):
            # 只匹配独立的"播放量"字符串，不匹配包含在其他词语中的
            if text.strip() == '播放量':
                # 查找附近的数字，支持'12345高'这种格式
                for j in range(max(0, i-3), min(len(texts), i+4)):
                    # 提取纯数字部分（包含逗号）
                    match = re.search(r'([\d,]+)', texts[j])
                    if match and re.match(r'^[\d,]+$', match.group(1).replace(',', '')):
                        metrics['播放量'] = match.group(1)
                        break
                break
        
        # 2. 完播率 - 查找独立的"完播率"字符串，然后在附近查找百分比
        for i, text in enumerate(texts):
            # 只匹配独立的"完播率"字符串
            if text.strip() == '完播率':
                # 优先向后搜索，避免匹配到前面的百分比数据
                found = False
                # 先向后搜索1-4个位置
                for j in range(i+1, min(len(texts), i+5)):
                    match = re.search(r'([\d.]+%)', texts[j])
                    if match:
                        metrics['完播率'] = match.group(1)
                        found = True
                        break
                # 如果向后没找到，再向前搜索1-2个位置
                if not found:
                    for j in range(max(0, i-2), i):
                        match = re.search(r'([\d.]+%)', texts[j])
                        if match:
                            metrics['完播率'] = match.group(1)
                            break
                break
        
        # 3. 平均播放时长 - 查找独立的"平均播放时长"字符串，然后在附近查找时长
        for i, text in enumerate(texts):
            # 只匹配独立的"平均播放时长"字符串
            if text.strip() == '平均播放时长':
                # 查找附近的时长，支持'12.5秒高'这种格式
                for j in range(max(0, i-3), min(len(texts), i+4)):
                    # 提取数字和秒的部分
                    match = re.search(r'([\d.]+秒)', texts[j])
                    if match:
                        metrics['平均播放时长'] = match.group(1)
                        break
                break
        
        # 4. 3s以上播放率 - 查找独立的"3s以上播放率"字符串，然后在附近查找百分比
        for i, text in enumerate(texts):
            # 只匹配独立的"3s以上播放率"字符串
            if text.strip() == '3s以上播放率':
                # 优先向后搜索，避免匹配到前面的百分比数据
                found = False
                # 先向后搜索1-4个位置
                for j in range(i+1, min(len(texts), i+5)):
                    match = re.search(r'([\d.]+%)', texts[j])
                    if match:
                        metrics['3s以上播放率'] = match.group(1)
                        found = True
                        break
                # 如果向后没找到，再向前搜索1-2个位置
                if not found:
                    for j in range(max(0, i-2), i):
                        match = re.search(r'([\d.]+%)', texts[j])
                        if match:
                            metrics['3s以上播放率'] = match.group(1)
                            break
                break
        
        # 5. 发布时间 - 查找时间格式，如'2025年07月22日17:20'
        publish_time_index = -1
        for i, text in enumerate(texts):
            # 匹配年月日时分格式：YYYY年MM月DD日HH:MM
            time_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日(\d{1,2}):(\d{1,2})', text)
            if time_match:
                year, month, day, hour, minute = time_match.groups()
                # 转换为目标格式：YYYY/MM/DD HH:MM
                formatted_time = f"{year}/{month.zfill(2)}/{day.zfill(2)} {hour.zfill(2)}:{minute.zfill(2)}"
                metrics['发布时间'] = formatted_time
                publish_time_index = i
                break
        
        # 6. 视频标题 - 查找位于'数据分析'和发布时间之间的文本
        data_analysis_index = -1
        for i, text in enumerate(texts):
            if text.strip() == '数据分析':
                data_analysis_index = i
                break
        
        # 如果找到了'数据分析'和发布时间的位置，在它们之间查找标题
        if data_analysis_index != -1 and publish_time_index != -1 and data_analysis_index < publish_time_index:
            for i in range(data_analysis_index + 1, publish_time_index):
                if i < len(texts):
                    text = texts[i].strip()
                    # 跳过一些明显不是标题的文本
                    if text and text not in ['×', '>', '<', '∠'] and not re.match(r'^\d{1,2}:\d{2}$', text):
                        # 如果文本包含#标签，提取#标签前的部分作为标题
                        if '#' in text:
                            title_part = text.split('#')[0].strip()
                            if title_part:
                                metrics['视频标题'] = title_part
                                break
                        # 如果文本长度合理且不是纯符号，可能是标题
                        elif len(text) > 2 and not re.match(r'^[×><∠]+$', text):
                            metrics['视频标题'] = text
                            break
        
        # 额外处理：基于示例数据的特定位置匹配
        if len(texts) > 20:  # 确保有足够的文本
            try:
                # 根据示例数据的位置关系进行匹配
                for i, text in enumerate(texts):
                    if text == '播放量' and i+1 < len(texts) and '播放量' not in metrics:
                        next_text = texts[i+1]
                        # 支持'12345高'这种格式，提取数字部分
                        match = re.search(r'([\d,]+)', next_text)
                        if match and re.match(r'^[\d,]+$', match.group(1).replace(',', '')):
                            metrics['播放量'] = match.group(1)
                    
                    elif text == '完播率' and i+1 < len(texts) and '完播率' not in metrics:
                        next_text = texts[i+1]
                        # 支持'81.24%高'这种格式，提取数字和百分号部分
                        match = re.search(r'([\d.]+%)', next_text)
                        if match:
                            metrics['完播率'] = match.group(1)
                    
                    elif text == '平均播放时长' and i+1 < len(texts) and '平均播放时长' not in metrics:
                        next_text = texts[i+1]
                        # 支持'12.5秒高'这种格式，提取数字和秒的部分
                        match = re.search(r'([\d.]+秒)', next_text)
                        if match:
                            metrics['平均播放时长'] = match.group(1)
                    
                    elif text == '3s以上播放率' and i+1 < len(texts) and '3s以上播放率' not in metrics:
                        next_text = texts[i+1]
                        # 支持'81.24%高'这种格式，提取数字和百分号部分
                        match = re.search(r'([\d.]+%)', next_text)
                        if match:
                            metrics['3s以上播放率'] = match.group(1)
            except IndexError:
                pass
        
    except Exception as e:
        print(f"解析数据时出错: {e}")
    
    return metrics

def extract_texts_from_ocr_result(result):
    """
    从OCR结果中提取文本列表
    
    Args:
        result: PaddleOCR的识别结果
    
    Returns:
        list: 提取的文本列表
    """
    all_texts = []
    
    if not result:
        return all_texts
    
    try:
        for res in result:
            # 检查res是否是字典类型，如果是则访问其中的数据
            if isinstance(res, dict) and 'res' in res:
                actual_res = res['res']
                if 'rec_texts' in actual_res:
                    all_texts.extend(actual_res['rec_texts'])
            elif hasattr(res, 'rec_texts'):
                all_texts.extend(res.rec_texts)
            elif hasattr(res, 'texts'):
                all_texts.extend(res.texts)
            else:
                # 如果res是字典，尝试直接访问
                if isinstance(res, dict):
                    for key in ['rec_texts', 'texts', 'text', 'result']:
                        if key in res:
                            if isinstance(res[key], list):
                                all_texts.extend(res[key])
                            elif isinstance(res[key], str):
                                all_texts.append(res[key])
                            break
    except Exception as e:
        print(f"提取文本时出错: {e}")
    
    return all_texts

@app.route('/upload', methods=['POST'])
def upload_image():
    """
    图片上传API接口
    
    请求参数:
        file: 上传的图片文件
    
    返回结果:
        JSON格式，包含保存的图片绝对路径
    """
    try:
        # 检查是否有文件在请求中
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有文件被上传',
                'data': None
            }), 400
        
        file = request.files['file']
        
        # 检查是否选择了文件
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '没有选择文件',
                'data': None
            }), 400
        
        # 检查文件类型
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'不支持的文件类型，支持的格式: {", ".join(ALLOWED_EXTENSIONS)}',
                'data': None
            }), 400
        
        # 生成随机文件名，保持原始扩展名
        original_extension = file.filename.rsplit('.', 1)[1].lower()
        random_filename = f"{uuid.uuid4().hex}.{original_extension}"
        
        # 构建保存路径
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], random_filename)
        absolute_path = os.path.abspath(file_path)
        
        # 保存文件
        file.save(file_path)
        
        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'data': {
                'file_path': absolute_path,
                'filename': random_filename,
                'original_filename': file.filename
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'上传失败: {str(e)}',
            'data': None
        }), 500

@app.route('/ocr/analyze', methods=['POST'])
def analyze_image():
    """
    OCR图片分析API接口
    
    请求参数:
        image_path: 图片路径（本地路径或URL）
    
    返回结果:
        JSON格式的视频数据指标
    """
    try:
        # 获取请求参数
        data = request.get_json()
        if not data or 'image_path' not in data:
            return jsonify({
                'success': False,
                'error': '缺少image_path参数',
                'data': None
            }), 400
        
        image_path = data['image_path'].strip()
        
        if not image_path:
            return jsonify({
                'success': False,
                'error': '图片路径不能为空',
                'data': None
            }), 400
        
        # 检查本地文件是否存在
        if not image_path.startswith('http') and not os.path.exists(image_path):
            return jsonify({
                'success': False,
                'error': f'文件不存在: {image_path}',
                'data': None
            }), 404
        
        # 执行OCR识别
        ocr_instance = None
        try:
            # 从池中获取OCR实例
            ocr_instance = ocr_pool.get_ocr(timeout=30)
            result = ocr_instance.predict(input=image_path)
            
            if not result:
                return jsonify({
                    'success': False,
                    'error': '未检测到文本内容',
                    'data': {
                        'total_play': None,
                        'complete_rate': None,
                        'avg_play_time': None,
                        '3s_above_rate': None,
                        'publish_time': None
                    }
                })
            
            # 提取文本
            all_texts = extract_texts_from_ocr_result(result)
            
            if not all_texts:
                return jsonify({
                    'success': False,
                    'error': '未能提取到文本内容',
                    'data': {
                        'total_play': None,
                        'complete_rate': None,
                        'avg_play_time': None,
                        '3s_above_rate': None,
                        'publish_time': None,
                        'video_title': None
                    }
                })
            
            # 解析视频指标
            metrics = parse_video_metrics(all_texts)
            
            # 确保返回所有4个字段
            avg_play_time_value = metrics.get('平均播放时长')
            # 如果平均播放时长包含'秒'字符，去掉它
            if avg_play_time_value and '秒' in str(avg_play_time_value):
                avg_play_time_value = str(avg_play_time_value).replace('秒', '')
            
            complete_rate_value = metrics.get('完播率')
            # 如果完播率包含'%'字符，去掉它
            if complete_rate_value and '%' in str(complete_rate_value):
                complete_rate_value = str(complete_rate_value).replace('%', '')
            
            three_s_above_rate_value = metrics.get('3s以上播放率')
            # 如果3s以上播放率包含'%'字符，去掉它
            if three_s_above_rate_value and '%' in str(three_s_above_rate_value):
                three_s_above_rate_value = str(three_s_above_rate_value).replace('%', '')
            
            result_data = {
                'total_play': metrics.get('播放量'),
                'complete_rate': complete_rate_value,
                'avg_play_time': avg_play_time_value,
                '3s_above_rate': three_s_above_rate_value,
                'publish_time': metrics.get('发布时间'),
                'video_title': metrics.get('视频标题')
            }
            
            response = jsonify({
                'success': True,
                'error': None,
                'data': result_data
            })
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            return response
            
        except Exception as ocr_error:
            return jsonify({
                'success': False,
                'error': f'OCR识别失败: {str(ocr_error)}',
                'data': None
            }), 500
        finally:
            # 确保OCR实例被返回到池中
            if ocr_instance is not None:
                ocr_pool.return_ocr(ocr_instance)
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器内部错误: {str(e)}',
            'data': None
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    健康检查接口
    """
    pool_status = ocr_pool.get_pool_status()
    return jsonify({
        'status': 'healthy',
        'ocr_status': 'ready' if pool_status['initialized'] else 'not_initialized',
        'ocr_pool': pool_status
    })

@app.route('/', methods=['GET'])
def index():
    """
    API文档首页
    """
    return jsonify({
        'name': 'PaddleOCR API Server',
        'version': '1.0.0',
        'endpoints': {
            'POST /upload': {
                'description': '上传图片文件到服务器',
                'parameters': {
                    'file': '图片文件（multipart/form-data）'
                },
                'response': {
                    'success': 'boolean',
                    'error': 'string or null',
                    'message': 'string',
                    'data': {
                        'file_path': '保存的图片绝对路径',
                        'filename': '生成的随机文件名',
                        'original_filename': '原始文件名'
                    }
                }
            },
            'POST /ocr/analyze': {
                'description': '分析图片并提取视频数据指标',
                'parameters': {
                    'image_path': '图片路径（本地路径或URL）'
                },
                'response': {
                    'success': 'boolean',
                    'error': 'string or null',
                    'data': {
                        'total_play': 'string or null', 
                        'complete_rate': 'string or null', 
                        'avg_play_time': 'string or null', 
                        '3s_above_rate': 'string or null' 
                    }
                }
            },
            'GET /health': {
                'description': '健康检查',
                'response': {
                    'status': 'string',
                    'ocr_initialized': 'boolean'
                }
            }
        },
        'example_request': {
            'url': 'POST /ocr/analyze',
            'body': {
                'image_path': './image/01.jpg'
            }
        }
    })

# 旧的 initialize_ocr 函数已被 OCRPool 类替代
# 保留此注释以说明代码变更

# 自动初始化（在模块导入时执行）
init_app()

if __name__ == '__main__':
    # 启动Flask服务器
    print("\n=== PaddleOCR HTTP API 服务器 ===")
    print("服务器启动中...")
    print("API文档: http://localhost:5000/")
    print("健康检查: http://localhost:5000/health")
    print("图片上传: POST http://localhost:5000/upload")
    print("OCR分析: POST http://localhost:5000/ocr/analyze")
    print("按 Ctrl+C 停止服务器")
    print("-" * 40)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )