import os
import sys
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load env variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

COUPANG_EMAIL = os.getenv("COUPANG_EMAIL")
COUPANG_PASSWORD = os.getenv("COUPANG_PASSWORD")

PROFILE_DIR = BASE_DIR / "scratch" / "coupang_profile"
SCREENSHOT_DIR = BASE_DIR / "docs" / "browser_screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def get_context(p, headless=True):
    """Launch persistent context with dedicated profile."""
    return p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        executable_path=CHROME_PATH,
        headless=headless,
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 900},
        locale="ko-KR",
        timezone_id="Asia/Seoul"
    )

def setup_login():
    """Launch headful Chrome to perform Coupang login once."""
    print("Launching Google Chrome in HEADFUL mode for Coupang Login...")
    print("This will open a browser window on the Mac Mini.")
    
    with sync_playwright() as p:
        context = get_context(p, headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(60000)
        
        print("Navigating to Coupang login page...")
        page.goto("https://login.coupang.com/login/login.pang")
        
        # Check if already logged in (redirected to main page)
        time.sleep(3)
        if "login" not in page.url:
            print("Already logged in! Active session detected.")
            context.close()
            return True
            
        # Fill credentials
        print("Filling credentials from .env...")
        email_selector = "#login-email-input"
        password_selector = "#login-password-input"
        
        try:
            page.wait_for_selector(email_selector, timeout=10000)
            page.fill(email_selector, COUPANG_EMAIL)
            page.fill(password_selector, COUPANG_PASSWORD)
            page.screenshot(path=str(SCREENSHOT_DIR / "setup_login_filled.png"))
            print("Credentials filled. Please complete Captcha or SMS Verification if prompted in the Chrome GUI.")
            print("Press Enter in this terminal once you have successfully logged in and see the Coupang homepage...")
            
            # We can also attempt to click the login button automatically
            page.click("button.login__button")
        except Exception as e:
            print("Login fields not found or already filled. Proceeding with manual check...")
            
        # Wait for user confirmation in the shell
        input(">>> PRESS ENTER HERE AFTER LOGIN IS COMPLETE IN THE CHROMIUM WINDOW <<<")
        
        # Verify login state
        page.goto("https://my.coupang.com/purchase/list")
        time.sleep(3)
        page.screenshot(path=str(SCREENSHOT_DIR / "setup_login_verified.png"))
        
        if "login" in page.url or "Access Denied" in page.title():
            print("Verification FAILED. Session not saved properly.")
            context.close()
            return False
            
        print("SUCCESS! Coupang login verified and session cookies saved in scratch/coupang_profile.")
        context.close()
        return True

def check_status():
    """Check if the session is currently logged in."""
    print("Checking Coupang login status...")
    with sync_playwright() as p:
        context = get_context(p, headless=True)
        page = context.pages[0] if context.pages else context.new_page()
        
        try:
            page.goto("https://my.coupang.com/purchase/list", wait_until="domcontentloaded")
            time.sleep(2)
            title = page.title()
            url = page.url
            
            if "login" in url or "Access Denied" in title:
                print("Status: NOT_LOGGED_IN")
                print(f"Details - URL: {url}, Title: {title}")
                context.close()
                return False
            else:
                print("Status: LOGGED_IN")
                print("Recent purchase history loaded successfully.")
                context.close()
                return True
        except Exception as e:
            print(f"Error checking status: {e}")
            context.close()
            return False

def add_to_cart_and_checkout(product_url, quantity=1):
    """Add a product to the cart and prepare checkout page (without buying)."""
    print(f"Adding product to cart: {product_url} (Qty: {quantity})...")
    
    with sync_playwright() as p:
        context = get_context(p, headless=True)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(30000)
        
        try:
            # 1. Load product page
            print("Loading product page...")
            page.goto(product_url)
            time.sleep(3)
            
            product_title = page.title()
            print(f"Product Title: {product_title}")
            page.screenshot(path=str(SCREENSHOT_DIR / "product_page.png"))
            
            # Check quantity selector (if needed and visible)
            # Usually we can just click 'Buy Now' directly which goes to Checkout!
            # Selecting '바로구매' (Buy Now) bypasses the Cart page entirely!
            buy_now_selectors = [
                "button.prod-buy-btn",
                "button:has-text('바로구매')",
                ".prod-buy-btn",
                "a:has-text('바로구매')"
            ]
            
            buy_now_btn = None
            for sel in buy_now_selectors:
                if page.query_selector(sel):
                    buy_now_btn = sel
                    break
                    
            if not buy_now_btn:
                print("Error: '바로구매' (Buy Now) button not found.")
                page.screenshot(path=str(SCREENSHOT_DIR / "product_buy_now_error.png"))
                context.close()
                return {"ok": False, "error": "Buy Now button not found"}
                
            print(f"Clicking Buy Now using selector: {buy_now_btn}...")
            page.click(buy_now_btn)
            time.sleep(4)
            
            # 2. Verify we are on Checkout page
            print("Verifying checkout page...")
            current_url = page.url
            print(f"Checkout URL: {current_url}")
            page.screenshot(path=str(SCREENSHOT_DIR / "checkout_page_loaded.png"))
            
            if "checkout" not in current_url:
                print("Error: Did not redirect to checkout page.")
                context.close()
                return {"ok": False, "error": "Not on checkout page"}
                
            # Extract checkout details
            # Scrape order total price, shipping address
            total_price_selectors = [
                ".total-price",
                ".co-price-value",
                "strong:has-text('원')",
                "span:has-text('원')"
            ]
            
            price_text = "Unknown"
            for sel in total_price_selectors:
                el = page.query_selector(sel)
                if el:
                    price_text = el.inner_text().strip()
                    break
                    
            print(f"Detected Order Total Price: {price_text}")
            
            # Save final page HTML
            with open(SCREENSHOT_DIR / "checkout_order.html", "w", encoding="utf-8") as f:
                f.write(page.content())
                
            print("Checkout prepared successfully! Saving order state.")
            context.close()
            return {
                "ok": True,
                "product": product_title,
                "price": price_text,
                "checkout_url": current_url,
                "screenshot": str(SCREENSHOT_DIR / "checkout_page_loaded.png")
            }
        except Exception as e:
            print(f"Error preparing checkout: {e}")
            context.close()
            return {"ok": False, "error": str(e)}

def finalize_payment():
    """Click the final payment button to complete the purchase."""
    print("FINALIZING PAYMENT (Executing final order)...")
    
    with sync_playwright() as p:
        context = get_context(p, headless=True)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(30000)
        
        try:
            # 1. Navigate to the last checkout order
            print("Navigating to checkout...")
            # We can go directly to the Coupang cart and checkout
            page.goto("https://cart.coupang.com/cart/cart.pang")
            time.sleep(2)
            
            # Click checkout/payment button
            page.click("button.goPayment")
            time.sleep(3)
            
            print(f"Checkout page URL: {page.url}")
            page.screenshot(path=str(SCREENSHOT_DIR / "payment_final_page.png"))
            
            # Click final place order button
            # Usually: #co-payment-btn or button#co-payment-btn
            pay_btn_selectors = [
                "#co-payment-btn",
                "button:has-text('결제하기')",
                "button.co-payment-btn",
                "#payment-btn"
            ]
            
            pay_btn = None
            for sel in pay_btn_selectors:
                if page.query_selector(sel):
                    pay_btn = sel
                    break
                    
            if not pay_btn:
                print("Error: Final payment button not found.")
                context.close()
                return {"ok": False, "error": "Payment button not found"}
                
            print(f"Clicking final payment button: {pay_btn}...")
            page.click(pay_btn)
            time.sleep(5)
            
            page.screenshot(path=str(SCREENSHOT_DIR / "payment_completed.png"))
            print("Payment click complete. Verification screenshot saved.")
            context.close()
            return {"ok": True}
        except Exception as e:
            print(f"Error finalizing payment: {e}")
            context.close()
            return {"ok": False, "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Coupang Automation Order Tool")
    parser.add_argument("action", choices=["setup", "status", "cart", "pay"])
    parser.add_argument("--url", help="Product URL (required for cart)")
    parser.add_argument("--qty", type=int, default=1, help="Quantity (default: 1)")
    
    args = parser.parse_args()
    
    if args.action == "setup":
        success = setup_login()
        sys.exit(0 if success else 1)
    elif args.action == "status":
        success = check_status()
        sys.exit(0 if success else 1)
    elif args.action == "cart":
        if not args.url:
            print("Error: --url is required for cart action.")
            sys.exit(1)
        result = add_to_cart_and_checkout(args.url, args.qty)
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result["ok"] else 1)
    elif args.action == "pay":
        result = finalize_payment()
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result["ok"] else 1)

if __name__ == "__main__":
    main()
