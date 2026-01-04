#!/usr/bin/env python3
"""
1688 智能报价系统 - Python 版本
"""

import os
import sys
import json
import time
import uuid
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import subprocess

# 获取脚本目录
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd())
# 使用环境变量 PORT（Railway/Render 等平台会设置），默认 8080
PORT = int(os.environ.get("PORT", 8080))
UPLOAD_DIR = SCRIPT_DIR / "uploads"
STATIC_DIR = SCRIPT_DIR / "static"

UPLOAD_DIR.mkdir(exist_ok=True)

class QuoteHandler(SimpleHTTPRequestHandler):
    """自定义 HTTP 处理器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SCRIPT_DIR), **kwargs)
    
    def end_headers(self):
        """添加禁用缓存的头"""
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def do_GET(self):
        """处理 GET 请求"""
        parsed = urlparse(self.path)
        
        if parsed.path == "/" or parsed.path == "":
            self.path = "/static/index.html"
            return super().do_GET()
        
        elif parsed.path == "/api/health":
            self.send_json_response({"status": "ok", "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            return
        
        elif parsed.path.startswith("/api/uploads/"):
            filename = parsed.path.split("/")[-1]
            filepath = UPLOAD_DIR / filename
            if filepath.exists():
                self.send_response(200)
                content_type = "image/jpeg"
                if filename.endswith(".png"):
                    content_type = "image/png"
                self.send_header("Content-Type", content_type)
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "File not found")
                return
        
        return super().do_GET()
    
    def do_POST(self):
        """处理 POST 请求"""
        parsed = urlparse(self.path)
        
        if parsed.path == "/api/search":
            self.handle_search()
            return
        
        self.send_error(404, "Not Found")
    
    def handle_search(self):
        """处理图片搜索请求"""
        try:
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self.send_json_response({"success": False, "message": "请上传图片文件"}, 400)
                return
            
            boundary = content_type.split("boundary=")[-1].encode()
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            
            parts = body.split(b"--" + boundary)
            image_data = None
            filename = "upload.jpg"
            
            for part in parts:
                if b"filename=" in part:
                    header_end = part.find(b"\r\n\r\n")
                    if header_end != -1:
                        header = part[:header_end].decode("utf-8", errors="ignore")
                        if 'filename="' in header:
                            filename = header.split('filename="')[1].split('"')[0]
                        image_data = part[header_end + 4:]
                        if image_data.endswith(b"\r\n"):
                            image_data = image_data[:-2]
            
            if not image_data:
                self.send_json_response({"success": False, "message": "未找到图片文件"}, 400)
                return
            
            ext = Path(filename).suffix or ".jpg"
            save_filename = f"{uuid.uuid4().hex}{ext}"
            save_path = UPLOAD_DIR / save_filename
            
            with open(save_path, "wb") as f:
                f.write(image_data)
            
            print(f"📷 图片已保存: {save_path}")
            
            result = self.search_1688(str(save_path))
            self.send_json_response(result)
            
        except Exception as e:
            print(f"❌ 搜索错误: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"success": False, "message": f"搜索失败: {str(e)}"}, 500)
    
    def search_1688(self, image_path: str) -> dict:
        """使用 Playwright 搜索 1688"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("⚠️  Playwright 未安装，返回模拟数据")
            return self.get_mock_data(image_path)
        
        # 检查是否有已登录的浏览器数据
        # 尝试不使用登录，直接访问
        print("🌐 使用普通浏览器模式...")
        
        print(f"🔍 开始搜索: {image_path}")
        products = []
        search_url = ""
        
        try:
            with sync_playwright() as p:
                # 使用普通浏览器 - 中文界面（但提取USD/销量/Super Factory等信息）
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="zh-CN"
                )
                page = context.new_page()
                
                # 直接访问图搜页面
                print("📡 访问 1688 图搜页面...")
                page.goto("https://pages-fast.1688.com/wow/cbu/srch_rec/image_search/youyuan/index.html", 
                         timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                
                # 检查是否被重定向到登录页
                if "login" in page.url.lower():
                    print("⚠️  需要登录才能使用图搜功能")
                    context.close()
                    return self.get_mock_data(image_path)
                
                print("📤 上传图片...")
                file_inputs = page.locator('input[type="file"]').all()
                if file_inputs:
                    file_inputs[0].set_input_files(image_path)
                    page.wait_for_timeout(3000)
                    print("   ✅ 图片已上传")
                    
                    # 点击搜索按钮 - 尝试多种方式
                    print("🔍 点击搜索按钮...")
                    search_clicked = False
                    
                    # 尝试各种可能的搜索按钮
                    search_selectors = [
                        "text=搜索图片",         # 图搜按钮（右侧）
                        "text=Search for",      # 英文版
                        "button:has-text('搜索图片')",
                        "[class*='search-btn']",
                        "text=搜索",            # 通用搜索
                    ]
                    
                    for selector in search_selectors:
                        try:
                            page.click(selector, timeout=2000)
                            print(f"   ✅ 点击成功: {selector}")
                            search_clicked = True
                            break
                        except:
                            continue
                    
                    if not search_clicked:
                        print("   ⚠️  未找到搜索按钮，尝试按 Enter 键")
                        page.keyboard.press("Enter")
                    
                    print("⏳ 等待搜索结果...")
                    page.wait_for_timeout(8000)
                    
                    # 检查是否有结果
                    page_text = page.inner_text('body')
                    if 'empty' in page_text.lower() or '空空如也' in page_text:
                        print("   ⚠️ 首次搜索为空，等待重试...")
                        page.wait_for_timeout(5000)
                    
                    # 滚动页面加载更多商品
                    print("📜 滚动页面加载更多...")
                    for _ in range(6):
                        page.evaluate("window.scrollBy(0, 600)")
                        page.wait_for_timeout(1200)
                    
                    page.wait_for_timeout(2000)
                
                search_url = page.url
                print(f"🔗 搜索URL: {search_url[:80]}...")
                
                # 截图用于调试
                debug_path = UPLOAD_DIR / "debug_search.png"
                page.screenshot(path=str(debug_path))
                print(f"📸 调试截图: {debug_path}")
                
                print("📊 提取商品数据...")
                products = page.evaluate("""
                    () => {
                        const products = [];
                        
                        // 遍历所有商品图片
                        const imgs = document.querySelectorAll('img[src*="cbu01"], img[src*="alicdn.com"]');
                        
                        imgs.forEach((img, idx) => {
                            if (idx > 100 || products.length >= 15) return;
                            if (img.width < 80 || img.height < 80) return;
                            
                            // 向上查找商品卡片容器
                            let container = img.parentElement;
                            for (let i = 0; i < 8 && container; i++) {
                                const text = container.innerText || '';
                                
                                if (text.includes('¥') || text.includes('￥') || text.includes('$')) {
                                    const priceMatch = text.match(/[¥￥]\\s*(\\d+\\.?\\d*)/);
                                    if (!priceMatch) {
                                        container = container.parentElement;
                                        continue;
                                    }
                                    
                                    // 提取标题
                                    let title = '';
                                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                                    for (const line of lines) {
                                        if (line.includes('图搜') || line.includes('比价') || line.includes('同款')) continue;
                                        if (line.includes('点击') || line.includes('上传') || line.includes('本地')) continue;
                                        if (line.includes('¥') || line.includes('$') || line.includes('Rate')) continue;
                                        if (line.includes('入驻') || line.includes('sold')) continue;
                                        if (line.startsWith('1、') || line.startsWith('2、')) continue;
                                        if (line.length > 8 && line.length < 80) {
                                            title = line;
                                            break;
                                        }
                                    }
                                    
                                    if (!title || title.length < 6) {
                                        container = container.parentElement;
                                        continue;
                                    }
                                    
                                    // ===== 提取USD价格 (如 ≈$5.70 或 $5.70) =====
                                    let usdPrice = '';
                                    const usdMatch = text.match(/[≈≃]?\\s*\\$\\s*(\\d+\\.?\\d*)/);
                                    if (usdMatch) usdPrice = '$' + usdMatch[1];
                                    
                                    // ===== 提取销量 =====
                                    let soldCount = '';
                                    // 英文: "1K+ sold", "8K+ sold", "900+ sold"
                                    let soldMatch = text.match(/(\\d+[KkMm]?\\+?)\\s*sold/i);
                                    if (!soldMatch) {
                                        // 中文: "成交123笔", "已售1000+", "销量1234"
                                        soldMatch = text.match(/(?:成交|已售|销量)[：:\\s]*(\\d+[万+]*)/);
                                    }
                                    if (!soldMatch) {
                                        // 中文: "123件" 
                                        soldMatch = text.match(/(\\d{2,})[+]?件/);
                                    }
                                    if (soldMatch) soldCount = soldMatch[1] + (soldMatch[0].includes('sold') ? ' sold' : '件');
                                    
                                    // ===== 提取回购率 =====
                                    let repurchaseRate = '';
                                    const rateMatch = text.match(/(?:Repurchase Rate|回头率|回购率)[：:\\s]*(\\d+)%?/i);
                                    if (rateMatch) repurchaseRate = rateMatch[1] + '%';
                                    
                                    // ===== 优质厂家标记 =====
                                    const superFactory = text.includes('Super Factory') || text.includes('优质厂家') || 
                                                        text.includes('实力厂家') || text.includes('牛头') || text.includes('金牌');
                                    
                                    // ===== Choice标记 =====
                                    const isChoice = text.includes('Choice') || text.includes('精选');
                                    
                                    // ===== 热销标记 =====
                                    const hotSelling = text.includes('Hot selling') || text.includes('热销') || 
                                                       text.includes('爆款') || text.includes('火爆');
                                    
                                    // ===== 供应商 =====
                                    let supplier = '';
                                    const supplierMatch = text.match(/入驻(\\d+)年\\s*([^\\n¥$]+)/);
                                    if (supplierMatch) {
                                        supplier = supplierMatch[2].trim().slice(0, 25);
                                    }
                                    
                                    // 包邮标记
                                    const freeShipping = text.includes('包邮') || text.includes('免运费') || text.includes('Free shipping');
                                    
                                    products.push({
                                        title: title.slice(0, 100),
                                        price: priceMatch[1],
                                        usd_price: usdPrice,
                                        image_url: img.src,
                                        product_url: '',
                                        sold: soldCount,
                                        repurchase_rate: repurchaseRate,
                                        super_factory: superFactory,
                                        is_choice: isChoice,
                                        hot_selling: hotSelling,
                                        supplier: supplier,
                                        shipping: freeShipping ? '包邮' : '',
                                        weight: ''
                                    });
                                    
                                    break;
                                }
                                container = container.parentElement;
                            }
                        });
                        
                        // 去重
                        const seen = new Set();
                        return products.filter(p => {
                            const key = p.title.slice(0, 20) + p.price;
                            if (seen.has(key)) return false;
                            seen.add(key);
                            return true;
                        }).slice(0, 12);
                    }
                """)
                
                # 通过点击商品图片获取详细信息
                print(f"📦 点击获取 {len(products)} 个商品的详细信息...")
                
                for i, product in enumerate(products):
                    if i >= 12:  # 限制数量
                        break
                    try:
                        img_url = product.get('image_url', '')
                        if not img_url:
                            continue
                        
                        # 滚动到商品可见位置
                        row = i // 3
                        page.evaluate(f"window.scrollTo(0, {row * 350 + 300})")
                        page.wait_for_timeout(500)
                        
                        # 点击商品图片
                        clicked = False
                        
                        # 提取图片关键标识
                        img_key = ''
                        if 'cbu01' in img_url:
                            parts = img_url.split('/')
                            for p in parts:
                                if p.startswith('O1CN') or (len(p) > 10 and '.' not in p):
                                    img_key = p[:15]
                                    break
                        
                        # 方法1: 使用图片关键标识匹配
                        if img_key:
                            try:
                                page.click(f'img[src*="{img_key}"]', timeout=2000)
                                clicked = True
                            except:
                                pass
                        
                        # 方法2: 通过索引点击搜索结果中的图片
                        if not clicked:
                            try:
                                # 搜索结果区域的图片（排除顶部上传预览区）
                                result_imgs = page.locator('img[src*="cbu01"][width]')
                                count = result_imgs.count()
                                if count > i:
                                    result_imgs.nth(i).click(timeout=2000)
                                    clicked = True
                            except:
                                pass
                        
                        if not clicked:
                            print(f"   ⚠️ 商品{i+1}: 无法点击")
                            continue
                        
                        # 等待新页面
                        page.wait_for_timeout(3500)
                        
                        # 检查新窗口
                        all_pages = context.pages
                        if len(all_pages) > 1:
                            detail_page = all_pages[-1]
                            detail_page.wait_for_timeout(3000)
                            
                            # 尝试点击SKU选项来触发运费显示
                            sku_clicked = False
                            try:
                                # 关闭可能的弹窗
                                try:
                                    close_btns = detail_page.locator('[class*="close"], [class*="Close"], button:has-text("×")')
                                    if close_btns.count() > 0:
                                        close_btns.first.click(timeout=1000)
                                        detail_page.wait_for_timeout(500)
                                except:
                                    pass
                                
                                # 滚动到SKU区域
                                detail_page.evaluate("window.scrollTo(0, 300)")
                                detail_page.wait_for_timeout(500)
                                
                                # 方法1: 点击颜色选项（多种选择器）
                                color_selectors = [
                                    'img[class*="sku"]',
                                    'img[class*="color"]', 
                                    'img[class*="Color"]',
                                    '[class*="sku-item"] img',
                                    '[class*="skuList"] img',
                                    '[data-sku] img'
                                ]
                                for sel in color_selectors:
                                    try:
                                        el = detail_page.locator(sel).first
                                        if el.is_visible(timeout=500):
                                            el.click(timeout=1500)
                                            sku_clicked = True
                                            detail_page.wait_for_timeout(1000)
                                            break
                                    except:
                                        continue
                                
                                # 方法2: 点击尺码选项
                                if sku_clicked:
                                    size_selectors = [
                                        '[class*="size"] span',
                                        '[class*="Size"] span',
                                        '[class*="sku-size"] span',
                                        '[class*="skuList"] span'
                                    ]
                                    for sel in size_selectors:
                                        try:
                                            el = detail_page.locator(sel).first
                                            if el.is_visible(timeout=500):
                                                el.click(timeout=1500)
                                                detail_page.wait_for_timeout(1000)
                                                break
                                        except:
                                            continue
                                
                                # 等待运费信息加载
                                if sku_clicked:
                                    detail_page.wait_for_timeout(1500)
                                    
                            except Exception as e:
                                pass  # 忽略SKU点击失败
                            
                            # 提取详情 - 包含表格重量提取和SKU运费
                            detail = detail_page.evaluate(r"""
                                () => {
                                    const text = document.body.innerText;
                                    const result = { weight: '', shipping: '', supplier: '' };
                                    
                                    // 供应商
                                    const supplierEls = document.querySelectorAll('[class*="company"], [class*="shop"], [class*="seller"]');
                                    for (const el of supplierEls) {
                                        const t = el.innerText.trim();
                                        if (t.length > 4 && t.length < 50 && !t.includes('¥') &&
                                            (t.includes('公司') || t.includes('厂') || t.includes('店') || t.includes('商行'))) {
                                            result.supplier = t.split('\n')[0];
                                            break;
                                        }
                                    }
                                    
                                    // ===== 重量提取 - 多种方式 =====
                                    
                                    // 方法1: 从包装信息表格提取（表头包含"重量(g)"）
                                    const tables = document.querySelectorAll('table');
                                    for (const table of tables) {
                                        if (result.weight) break;
                                        const headerRow = table.querySelector('tr');
                                        if (headerRow) {
                                            const headers = Array.from(headerRow.querySelectorAll('th, td')).map(h => h.innerText.trim());
                                            const weightIdx = headers.findIndex(h => h.includes('重量'));
                                            if (weightIdx >= 0) {
                                                const dataRows = table.querySelectorAll('tr');
                                                if (dataRows.length > 1) {
                                                    const cells = dataRows[1].querySelectorAll('td');
                                                    if (cells[weightIdx]) {
                                                        const w = cells[weightIdx].innerText.trim();
                                                        if (/^\d{2,5}$/.test(w)) {
                                                            result.weight = w;
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    
                                    // 方法2: 从商品属性区域提取
                                    if (!result.weight) {
                                        const attrMatch = text.match(/重量[（(]?[gG克]?[)）]?[：:\s]*(\d{2,5})/);
                                        if (attrMatch) result.weight = attrMatch[1];
                                    }
                                    
                                    // 方法3: 从文本中提取 "净重/毛重: XXXg"
                                    if (!result.weight) {
                                        const patterns = [
                                            /净重[：:\s]*(\d+\.?\d*)\s*[gG克]/,
                                            /毛重[：:\s]*(\d+\.?\d*)\s*[gG克]/,
                                            /单品重量[：:\s]*(\d+\.?\d*)/
                                        ];
                                        for (const p of patterns) {
                                            const m = text.match(p);
                                            if (m && parseFloat(m[1]) > 10 && parseFloat(m[1]) < 50000) {
                                                result.weight = m[1];
                                                break;
                                            }
                                        }
                                    }
                                    
                                    // 方法4: 匹配类似 "500g" 的格式
                                    if (!result.weight) {
                                        const m = text.match(/(\d{3,4})\s*[gG克]\b/);
                                        if (m && parseFloat(m[1]) > 50 && parseFloat(m[1]) < 5000) {
                                            result.weight = m[1];
                                        }
                                    }
                                    
                                    // ===== 运费提取 (增强版) =====
                                    // 优先检查包邮
                                    if (text.includes('包邮') || text.includes('Free shipping') || text.includes('免运费') || text.includes('0运费')) {
                                        // 检查是否有条件包邮 (如"满30包邮")
                                        const condMatch = text.match(/满(\d+)包邮/);
                                        if (condMatch) {
                                            result.shipping = '满' + condMatch[1] + '包邮';
                                        } else {
                                            result.shipping = '包邮';
                                        }
                                    } else {
                                        let shipMatch = null;
                                        
                                        // 方法1: 匹配 "另需运费 (预估): ¥3" 或 "另需运费(预估):¥3"
                                        shipMatch = text.match(/另需运费[^¥￥]*[¥￥]\s*(\d+\.?\d*)/);
                                        
                                        // 方法2: 匹配 "预估): ¥3" 格式
                                        if (!shipMatch) {
                                            shipMatch = text.match(/预估\)?[：:\s]*[¥￥]\s*(\d+\.?\d*)/);
                                        }
                                        
                                        // 方法3: 匹配 "运费(预估): ¥X"
                                        if (!shipMatch) {
                                            shipMatch = text.match(/运费[（(]?预估[)）]?[：:\s]*[¥￥]?\s*(\d+\.?\d*)/i);
                                        }
                                        
                                        // 方法4: 匹配底部的运费信息 "运费: ¥X"
                                        if (!shipMatch) {
                                            shipMatch = text.match(/(?:^|\s)运费[：:\s]+[¥￥]\s*(\d+\.?\d*)/m);
                                        }
                                        
                                        // 方法5: 匹配 "快递: ¥X"
                                        if (!shipMatch) {
                                            shipMatch = text.match(/快递[费]?[：:\s]*[¥￥]\s*(\d+\.?\d*)/i);
                                        }
                                        
                                        // 方法6: 从页面元素直接提取
                                        if (!shipMatch) {
                                            const shippingEls = document.querySelectorAll('[class*="freight"], [class*="shipping"], [class*="delivery"]');
                                            for (const el of shippingEls) {
                                                const t = el.innerText;
                                                const m = t.match(/[¥￥]\s*(\d+\.?\d*)/);
                                                if (m && parseFloat(m[1]) > 0 && parseFloat(m[1]) < 100) {
                                                    shipMatch = m;
                                                    break;
                                                }
                                            }
                                        }
                                        
                                        if (shipMatch && parseFloat(shipMatch[1]) > 0 && parseFloat(shipMatch[1]) < 100) {
                                            result.shipping = '¥' + shipMatch[1];
                                        }
                                    }
                                    
                                    // ===== 店铺评分/星级 =====
                                    const ratingMatch = text.match(/(\d+\.?\d*)\s*(?:分|星|评分)/);
                                    if (ratingMatch && parseFloat(ratingMatch[1]) <= 5) {
                                        result.rating = ratingMatch[1];
                                    }
                                    
                                    return result;
                                }
                            """)
                            
                            if detail and (detail.get('weight') or detail.get('supplier')):
                                product.update(detail)
                                product['product_url'] = detail_page.url
                                # 显示更丰富的信息
                                weight_str = f"{detail.get('weight', '')}g" if detail.get('weight') else '-'
                                sold_str = product.get('sold', '-') or '-'
                                factory_tag = '⭐Super' if product.get('super_factory') else ''
                                supplier_str = (detail.get('supplier') or product.get('supplier', ''))[:18]
                                print(f"   ✅ 商品{i+1}: {weight_str} | 销量:{sold_str} | {factory_tag} {supplier_str}")
                            else:
                                print(f"   ⚠️ 商品{i+1}: 无详情")
                            
                            detail_page.close()
                        else:
                            print(f"   ⚠️ 商品{i+1}: 未打开新窗口")
                            
                    except Exception as e:
                        print(f"   ⚠️ 商品{i+1}: {str(e)[:40]}")
                        try:
                            if len(context.pages) > 1:
                                context.pages[-1].close()
                        except:
                            pass
                
                context.close()
                
        except Exception as e:
            print(f"❌ Playwright 错误: {e}")
            import traceback
            traceback.print_exc()
            return self.get_mock_data(image_path)
        
        result = {
            "success": len(products) > 0,
            "message": f"成功找到 {len(products)} 个相关商品" if products else "未找到匹配的商品",
            "products": products,
            "search_url": search_url,
            "original_file": Path(image_path).name
        }
        
        if products:
            result["best_match"] = products[0]
        
        print(f"✅ 搜索完成，找到 {len(products)} 个商品")
        return result
    
    def get_mock_data(self, image_path: str) -> dict:
        """返回模拟数据（用于演示）"""
        mock_products = [
            {
                "title": "跨境羊羔绒男士卫衣秋冬季加绒加厚连帽运动服休闲开衫保暖外套",
                "price": "48.00",
                "image_url": "https://cbu01.alicdn.com/img/ibank/O1CN01example.jpg",
                "product_url": "https://detail.1688.com/offer/738313338034.html",
                "supplier": "石狮市镇谷服装厂",
                "tags": ["包邮", "7天无理由", "一件代发"],
                "weight": "763",
                "min_order": "1件起批"
            },
            {
                "title": "OOTD跨境欧码男款户外休闲运动连帽夹克拉链开衫口袋抓绒保暖卫衣",
                "price": "55.80",
                "image_url": "https://cbu01.alicdn.com/img/ibank/O1CN01example2.jpg",
                "product_url": "https://detail.1688.com/offer/999142619015.html",
                "supplier": "石狮泽言服装有限公司",
                "tags": ["包邮", "先采后付"],
                "weight": "763",
                "min_order": "1件起批"
            },
            {
                "title": "速卖通亚马逊秋冬季男士连帽加绒羊羔绒开衫卫衣大码外套潮流时尚",
                "price": "42.00",
                "image_url": "https://cbu01.alicdn.com/img/ibank/O1CN01example3.jpg",
                "product_url": "https://detail.1688.com/offer/748084224397.html",
                "supplier": "石狮市杉澈服装厂",
                "tags": ["7天无理由", "回头率52%"],
                "weight": "750",
                "min_order": "1件起批"
            },
            {
                "title": "跨境外贸秋冬男款卫衣运动健身休闲卫衣开衫连帽外套",
                "price": "21.99",
                "image_url": "https://cbu01.alicdn.com/img/ibank/O1CN01example4.jpg",
                "product_url": "https://detail.1688.com/offer/819234640754.html",
                "supplier": "上饶市奇特服饰有限公司",
                "tags": ["券后价", "先采后付"],
                "weight": "680",
                "min_order": "1件起批"
            }
        ]
        
        return {
            "success": True,
            "message": f"演示模式: 找到 {len(mock_products)} 个相关商品（安装 Playwright 后可获取真实数据）",
            "products": mock_products,
            "best_match": mock_products[0],
            "search_url": "https://s.1688.com/youyuan/index.htm",
            "original_file": Path(image_path).name
        }
    
    def send_json_response(self, data: dict, status: int = 200):
        """发送 JSON 响应"""
        response = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(response))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response)
    
    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{time.strftime('%H:%M:%S')}] {args[0]}")


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           🚀 1688 智能报价系统 - Python 版                   ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 检查 Playwright
    try:
        import playwright
        print("✅ Playwright 已安装")
    except ImportError:
        print("⚠️  Playwright 未安装，将使用演示模式")
        print("   安装命令: pip3 install playwright && playwright install chromium")
    
    server = HTTPServer(("0.0.0.0", PORT), QuoteHandler)
    
    print(f"""
📡 服务已启动！

🌐 访问地址: http://localhost:{PORT}

💡 使用说明:
   1. 在浏览器中打开上述地址
   2. 上传或拖拽商品图片
   3. 点击"开始搜索"按钮

按 Ctrl+C 停止服务...
    """)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
