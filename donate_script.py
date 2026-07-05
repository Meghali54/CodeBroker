import webbrowser
import urllib.parse

def open_donation_page():
    """
    Opens the default web browser to the PayPal donation page for Code Broker.
    """
    recipient_email = "samiratra95@gmail.com"
    item_name = "Code Broker Donation"
    currency_code = "USD"
    
    # Construct the PayPal donation URL
    params = {
        "cmd": "_donations",
        "business": recipient_email,
        "item_name": item_name,
        "currency_code": currency_code,
    }
    
    base_url = "https://www.paypal.com/cgi-bin/webscr"
    donation_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    print(f"Directing you to PayPal to donate to {recipient_email}...")
    print(f"URL: {donation_url}")
    
    try:
        webbrowser.open(donation_url)
        print("Browser opened successfully.")
    except Exception as e:
        print(f"Failed to open browser: {e}")
        print("Please copy and paste the URL above into your browser.")

if __name__ == "__main__":
    open_donation_page()
