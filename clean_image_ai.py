from PIL import Image
import sys
import os
from datetime import datetime

def clean_image_metadata(input_path, output_path=None):
    """
    清理图片中的元数据
    :param input_path: 输入图片路径
    :param output_path: 输出图片路径，如果不指定则使用时间戳创建新文件
    """
    try:
        # 打开图片
        with Image.open(input_path) as img:
            # 创建一个新的图片，只复制像素数据，不复制元数据
            cleaned_img = Image.new(img.mode, img.size)
            cleaned_img.putdata(list(img.getdata()))
            
            # 如果没有指定输出路径，则使用时间戳创建新文件名
            if output_path is None:
                # 获取输入文件的目录和扩展名
                input_dir = os.path.dirname(input_path) or '.'
                _, ext = os.path.splitext(input_path)
                # 生成时间戳文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = os.path.join(input_dir, f'cleaned_{timestamp}{ext}')
                
            # 保存清理后的图片
            cleaned_img.save(output_path, "PNG")
            print(f"已成功清理图片: {output_path}")
            
            # 删除原文件
            if output_path != input_path:  # 确保输出路径与输入路径不同时才删除
                os.remove(input_path)
                print(f"已删除原文件: {input_path}")
            
    except Exception as e:
        print(f"处理图片时出错: {str(e)}")
        return False
        
    return True

def main():
    if len(sys.argv) < 2:
        print("使用方法: python clean_image_ai.py <输入图片路径> [输出图片路径]")
        return
        
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_path):
        print(f"错误: 找不到输入文件 {input_path}")
        return
        
    clean_image_metadata(input_path, output_path)

if __name__ == "__main__":
    main()