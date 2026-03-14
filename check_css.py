from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('http://localhost:8085/admin.html')
    
    # Switch to list view
    page.click('#btn-view-list')
    page.wait_for_timeout(1000)
    
    # Get computed styles
    result = page.evaluate('''() => {
        const card = document.querySelector('.dashboard-card');
        const content = card.querySelector('.card-content');
        const title = card.querySelector('.card-title');
        return {
            card_class: card.className,
            card_display: window.getComputedStyle(card).display,
            card_grid_cols: window.getComputedStyle(card).gridTemplateColumns,
            content_display: window.getComputedStyle(content).display,
            title_display: window.getComputedStyle(title).display,
            title_font_size: window.getComputedStyle(title).fontSize,
            title_color: window.getComputedStyle(title).color,
            card_padding: window.getComputedStyle(card).padding
        };
    }''')
    
    print(json.dumps(result, indent=2))
    browser.close()
