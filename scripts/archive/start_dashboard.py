"""
启动三方法对比看板
用法: python scripts/start_dashboard.py
"""
import os
import sys
import webbrowser
import http.server
import socketserver
from pathlib import Path
import threading
import time

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
DASHBOARD_DIR = PROJECT_ROOT / "tools" / "comparison_dashboard"
DATA_FILE = DASHBOARD_DIR / "data" / "merged.json"

PORT = 8080


def run_preprocess():
    """运行数据预处理"""
    print("正在预处理数据...")
    preprocess_script = DASHBOARD_DIR / "preprocess.py"

    # 切换到dashboard目录执行预处理
    original_dir = os.getcwd()
    os.chdir(DASHBOARD_DIR)

    try:
        # 导入并执行预处理
        sys.path.insert(0, str(DASHBOARD_DIR))
        from preprocess import merge_data
        merge_data()
    finally:
        os.chdir(original_dir)
        if str(DASHBOARD_DIR) in sys.path:
            sys.path.remove(str(DASHBOARD_DIR))


def start_server():
    """启动HTTP服务器"""
    os.chdir(DASHBOARD_DIR)

    handler = http.server.SimpleHTTPRequestHandler
    handler.extensions_map.update({
        '.js': 'application/javascript',
        '.json': 'application/json',
    })

    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"\n看板已启动: http://localhost:{PORT}")
        print("按 Ctrl+C 停止服务器\n")
        httpd.serve_forever()


def open_browser():
    """延迟打开浏览器"""
    time.sleep(1)
    webbrowser.open(f"http://localhost:{PORT}")


def main():
    # 检查数据文件
    if not DATA_FILE.exists():
        print(f"数据文件不存在: {DATA_FILE}")
        run_preprocess()

    if not DATA_FILE.exists():
        print("错误: 预处理失败，无法生成数据文件")
        sys.exit(1)

    print(f"数据文件: {DATA_FILE}")

    # 在后台线程打开浏览器
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # 启动服务器（主线程）
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except OSError as e:
        if "Address already in use" in str(e) or "Only one usage" in str(e):
            print(f"端口 {PORT} 已被占用，请关闭占用该端口的程序或更换端口")
        else:
            raise


if __name__ == "__main__":
    main()
