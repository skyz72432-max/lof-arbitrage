"""
Configuration module for Jisilu LOF scraper
Provides centralized configuration management with low coupling
"""
import os
from typing import Dict

class Config:
    """Configuration class with environment variable support"""
    
    # Jisilu URLs
    BASE_URL = "https://www.jisilu.cn"
    LOF_DETAIL_URL = f"{BASE_URL}/data/lof/hist_list/"
    QDII_DETAIL_URL = f"{BASE_URL}/data/qdii/hist_list/"
    
    # Request settings
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))
    
    # Rate limiting
    REQUESTS_PER_SECOND = float(os.getenv("REQUESTS_PER_SECOND", "2.0"))
    
    # Data storage
    DATA_DIR = os.getenv("DATA_DIR", "./data")
    CSV_ENCODING = "utf-8-sig"
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "lof_scraper.log")
    
    # Data retention
    MAX_DAYS_BACKUP = int(os.getenv("MAX_DAYS_BACKUP", "90"))
    
    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        """Get HTTP headers for requests"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': cls.BASE_URL
        }
    
    @classmethod
    def create_data_dir(cls):
        """Create data directory if it doesn't exist"""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        
    @classmethod
    def get_lof_codes(cls) -> list:
        """Get LOF codes from file"""
        try:
            # 获取当前脚本的绝对路径
            current_script_path = os.path.abspath(__file__)
            # 获取当前脚本所在目录
            current_script_dir = os.path.dirname(current_script_path)
            # 获取父目录
            parent_dir = os.path.dirname(current_script_dir)
            # 构建all_LOF.txt在父目录中的路径
            lof_file_path = os.path.join(parent_dir, 'all_LOF.txt')

            with open(lof_file_path, 'r', encoding='utf-8') as f:
                codes = [line.strip().replace("→", "").strip() for line in f if line.strip()]
                return [code for code in codes if code and code.isdigit()]
        except FileNotFoundError:
            return []