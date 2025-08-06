## API接口文档

### 1. 图片上传接口

**接口地址**: `POST /upload`

**请求方式**: `multipart/form-data`

**请求参数**:
- `file`: 图片文件（支持格式：png, jpg, jpeg, gif, bmp, tiff, webp）
- 文件大小限制：16MB

**响应格式**:
```json
{
    "success": true,
    "message": "文件上传成功",
    "data": {
        "file_path": "/absolute/path/to/ocr_images/random_filename.jpg",
        "filename": "random_filename.jpg",
        "original_filename": "original_image.jpg"
    }
}
```

**错误响应**:
```json
{
    "success": false,
    "error": "错误信息",
    "data": null
}
```

**字段说明**:
- `total_play`: 播放量，提取失败时为null
- `complete_rate`: 完播率（数值部分，不含%符号），提取失败时为null
- `avg_play_time`: 平均播放时长（数值部分，不含"秒"字符），提取失败时为null
- `3s_above_rate`: 3s以上播放率（数值部分，不含%符号），提取失败时为null
- `publish_time`: 视频发布时间，格式为"YYYY/MM/DD HH:MM"，提取失败时为null

**发布时间识别规则**:
- 自动识别OCR文本中的中文日期时间格式，如："2025年07月22日17:20"
- 转换为标准格式："2025/07/22 17:20"
- 支持单位数的月、日、时、分（会自动补零）

### 2. OCR分析接口

**接口地址**: `POST /ocr/analyze`

**请求参数**:
```json
{
    "image_path": "图片路径（本地路径或URL）"
}
```

**响应格式**:
```json
{
    "success": true,
    "error": null,
    "data": {
        "total_play": "2814", //播放量
        "complete_rate": "40.97", //完播率（已去除%符号）
        "avg_play_time": "38.35", //平均播放时长（已去除秒字符）
        "3s_above_rate": "81.33", //3s以上播放率（已去除%符号）
        "publish_time": "2025/07/22 17:20" //视频发布时间（格式：YYYY/MM/DD HH:MM）
    }
}
```

**错误响应**:
```json
{
    "success": false,
    "error": "错误信息",
    "data": null
}
### curl示例

```bash
# 1. 图片上传
curl -X POST http://10.3.10.213:5000/upload \
    -F "file=@./Desktop/_snapshot_10.100.0.19.png"

# 2. OCR分析（使用upload接口返回的文件路径）
curl -X POST http://10.3.10.213:5000/ocr/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/home/longene/ocr_images/40682432d3664c5ba73fa8e03211c060.png"}'

```

### 完整响应示例

**成功响应（包含发布时间）**:
```json
{
    "success": true,
    "error": null,
    "data": {
        "total_play": "284",
        "complete_rate": "40.76",
        "avg_play_time": "38.35",
        "3s_above_rate": "81.24",
        "publish_time": "2025/07/22 17:20"
    }
}
```

**部分字段缺失的响应**:
```json
{
    "success": true,
    "error": null,
    "data": {
        "total_play": "284",
        "complete_rate": null,
        "avg_play_time": "38.35",
        "3s_above_rate": "81.24",
        "publish_time": null
    }
}
```

### 3. LLM分析接口

**接口地址**: `POST /llm/analyze`

**请求参数**:
```json
{
    "image_path": "图片路径（本地路径或URL）"
}
```

**功能说明**:
- 使用大语言模型（qwen/qwen2.5-vl-72b-instruct:free）通过OpenRouter API分析图片
- 自动提取图片中的视频数据并返回JSON格式
- 支持视频标题提取（OCR接口已移除此功能）

**响应格式**:
```json
{
    "success": true,
    "error": null,
    "data": {
        "total_play": 1098, //播放量
        "complete_rate": "30.47%", //完播率
        "avg_play_time": "18.15秒", //平均播放时长
        "3s_above_rate": "41.2%", //3s以上播放率
        "publish_time": "2025/07/22 17:20", //发布时间
        "video_title": "哈哈哈" //视频标题
    }
}
```

**错误响应**:
```json
{
    "success": false,
    "error": "错误信息",
    "data": null
}
```

**注意事项**:
- 需要配置有效的OpenRouter API密钥
- 请求超时时间为60秒
- 返回的数据格式保持与图片中显示的字段名称一致
- LLM分析可能比OCR分析耗时更长但准确性更高

### curl示例

```bash
# LLM分析
curl -X POST http://localhost:5000/llm/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/path/to/your/image.jpg"}'
```

