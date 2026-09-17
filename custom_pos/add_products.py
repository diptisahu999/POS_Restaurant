import sys
import time
import xmlrpc.client

URL = "http://localhost:9981"
DB = "POS_restaurant"
USERNAME = "admin"
PASSWORD = "admin"

MENU_ITEMS = [
    # Soups
    {"name": "Thukpa Soup", "price": 220, "category": "Soups", "desc": "Hot & Spicy Noodle Soup with Fresh Vegetables"},
    {"name": "Vegetable Manchow Soup", "price": 220, "category": "Soups", "desc": "A dark brown, hot and spicy Indo-Chinese soup"},
    {"name": "Vegetable Hot & Sour Soup", "price": 220, "category": "Soups", "desc": "A spicy and tangy broth with finely chopped vegetables"},
    {"name": "Sweet Corn Soup", "price": 220, "category": "Soups", "desc": "A warm, slightly thick soup"},
    {"name": "Roasted Tomatoes Soup With Basil", "price": 220, "category": "Soups", "desc": "Sweet & Savoury Tomato Broth with Croutons"},
    {"name": "Cream Of Mushroom Soup", "price": 220, "category": "Soups", "desc": "Creamy mushroom broth with cheesy dumplings"},
    {"name": "Broccoli Almond Soup", "price": 220, "category": "Soups", "desc": "A healthy, creamy soup with broccoli and rich almonds"},
    {"name": "Tomato Soup", "price": 220, "category": "Soups", "desc": "A classic dish made primarily from tomatoes"},
    {"name": "Dal Dhaniya Shorba", "price": 220, "category": "Soups", "desc": "An Indian soup made with yellow moong dal, masoor dal, fresh coriander stems and whole spices"},

    # Salads
    {"name": "Citrus Crunch Salad", "price": 225, "category": "Salads", "desc": "Charred corn & onion with orange maple dressing"},
    {"name": "Garden Green Salad", "price": 225, "category": "Salads", "desc": "Carrot, Cucumber, Tomato, Onion, Chilli & Lemon"},
    {"name": "Som Tum Salad", "price": 225, "category": "Salads", "desc": "Raw papaya salad with Thai chilli & peanuts"},

    # Traditional & Asian Specials
    {"name": "Veg. Club Sandwich", "price": 220, "category": "Traditional & Asian Specials", "desc": "Three-layer sandwich made with toasted bread, fresh vegetables, spreads, and often cheese"},
    {"name": "Bombay Sandwich", "price": 200, "category": "Traditional & Asian Specials", "desc": "Soft white bread, butter, green coriander-mint chutney, and boiled potatoes"},
    {"name": "Veg Burger", "price": 200, "category": "Traditional & Asian Specials", "desc": "Vegetable patty inside a bun with lettuce, tomatoes, and sauces"},
    {"name": "Cheese Burger", "price": 220, "category": "Traditional & Asian Specials", "desc": "Vegetable and potato patty with a slice of cheese, crisp lettuce, and sliced tomatoes, served with tomato ketchup"},
    {"name": "Cheese Chilli Tossed", "price": 175, "category": "Traditional & Asian Specials", "desc": "Quick-baked canapé made with a balanced combination of cheese & chilli"},

    # Pizza
    {"name": "Margherita", "price": 220, "category": "Pizza", "desc": "Classic pizza topped with rich tomato sauce, fresh mozzarella, and aromatic basil"},
    {"name": "Veggie Pizza", "price": 230, "category": "Pizza", "desc": "Classic pizza topped with fresh vegetables, mozzarella cheese, and flavorful herbs"},
    {"name": "Paneer Tikka Pizza", "price": 230, "category": "Pizza", "desc": "Classic pizza topped with smoky paneer tikka, onions, capsicum, mozzarella cheese, and aromatic herbs"},

    # Asian Selection
    {"name": "Teriyaki Temple Noodles", "price": 275, "category": "Asian Selection", "desc": "Noodles with vegetables in teriyaki sauce"},
    {"name": "House Noodles", "price": 275, "category": "Asian Selection", "desc": "Wok-tossed noodles with vegetables"},
    {"name": "Butter Chilli Garlic Noodle", "price": 275, "category": "Asian Selection", "desc": "Noodles tossed in butter, chilli & garlic"},
    {"name": "Traditional Red Thai Curry", "price": 400, "category": "Asian Selection", "desc": "Steamed jasmine rice, vegetables & tofu in Thai-spiced coconut curry"},
    {"name": "Classic Burnt Garlic Fried Rice", "price": 200, "category": "Asian Selection", "desc": "Jasmine rice tossed in sesame oil & burnt garlic"},

    # Appetizers
    {"name": "Spicy Paneer Dumpling", "price": 300, "category": "Appetizers", "desc": "Crispy dumplings stuffed with paneer served with spicy sauce"},
    {"name": "Spring Roll Thai Style", "price": 270, "category": "Appetizers", "desc": "Traditional Thai wrap stuffed with juliennes of vegetables"},
    {"name": "Dry Manchurian", "price": 220, "category": "Appetizers", "desc": "Crispy deep-fried veg. balls tossed in a thick, sticky, and glossy umami sauce"},
    {"name": "Wok Tossed Dry Chilli Paneer", "price": 275, "category": "Appetizers", "desc": "Oriental spicy preparation of cottage cheese tossed with bell peppers and onions"},

    # Dim Sum Appetizers
    {"name": "Crispy Wonton", "price": 300, "category": "Dim Sum Appetizers", "desc": "Crispy stuffed wontons"},
    {"name": "Dim Sum", "price": 250, "category": "Dim Sum Appetizers", "desc": "House Surprise Dim Sum – Chef's special assorted dim sum"},
    {"name": "OG Paneer Tikka", "price": 350, "category": "Dim Sum Appetizers", "desc": "Paneer marinated in Indian spices"},
    {"name": "Tandoori Bharwan Mushrooms", "price": 375, "category": "Dim Sum Appetizers", "desc": "Mushrooms stuffed with spices & cheese"},
    {"name": "Dahi Ke Kebab", "price": 300, "category": "Dim Sum Appetizers", "desc": "Creamy kebab made with curd & kataifi"},
    {"name": "Peri Peri Paneer Tikka", "price": 350, "category": "Dim Sum Appetizers", "desc": "Paneer marinated in peri-peri sauce"},
    {"name": "Mutter Kaju Seekh Kebab", "price": 375, "category": "Dim Sum Appetizers", "desc": "Matar, cashew & peas kebabs"},
    {"name": "House Chaap", "price": 275, "category": "Dim Sum Appetizers", "desc": "Spicy tandoori chaap served with thecha"},

    # Pasta
    {"name": "Penne Alfredo Pasta", "price": 350, "category": "Pasta", "desc": "Creamy white sauce pasta"},
    {"name": "Spaghetti Aglio e Olio Pasta", "price": 350, "category": "Pasta", "desc": "Spaghetti in olive oil, garlic & parmesan"},
    {"name": "Penne Creamy Tomato Sauce Pasta", "price": 350, "category": "Pasta", "desc": "Penne in creamy tomato sauce"},
]

def execute_with_retry(models, DB, uid, pwd, model, method, *args, max_retries=5):
    for attempt in range(max_retries):
        try:
            return models.execute_kw(DB, uid, pwd, model, method, *args)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1.0)
            else:
                raise e

def run():
    print(f"Connecting to {URL}...", flush=True)
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    
    uid = None
    passwords_to_try = [PASSWORD, "admin", "admin123", "123", "1234"]
    used_pwd = PASSWORD
    for p in passwords_to_try:
        try:
            uid = common.authenticate(DB, USERNAME, p, {})
            if uid:
                used_pwd = p
                print(f"Authenticated as '{USERNAME}' (UID: {uid})", flush=True)
                break
        except Exception as e:
            print(f"Connection error: {e}", flush=True)
            time.sleep(1)

    if not uid:
        print("Could not authenticate. Please check your credentials.", flush=True)
        return

    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

    # 1. Categories
    categories = {}
    unique_cats = list({item['category'] for item in MENU_ITEMS})
    for cat_name in unique_cats:
        c_ids = execute_with_retry(models, DB, uid, used_pwd, 'pos.category', 'search', [[['name', '=', cat_name]]])
        if c_ids:
            categories[cat_name] = c_ids[0]
        else:
            cat_id = execute_with_retry(models, DB, uid, used_pwd, 'pos.category', 'create', [{'name': cat_name}])
            categories[cat_name] = cat_id
            print(f"Created category: {cat_name}", flush=True)
        time.sleep(0.1)

    # 2. Products
    success = 0
    for idx, item in enumerate(MENU_ITEMS, 1):
        cat_id = categories.get(item['category'])
        p_ids = execute_with_retry(models, DB, uid, used_pwd, 'product.template', 'search', [[['name', '=', item['name']]]])
        
        vals = {
            'name': item['name'],
            'list_price': float(item['price']),
            'available_in_pos': True,
            'description_sale': item['desc'],
        }
        if cat_id:
            vals['pos_categ_ids'] = [(6, 0, [cat_id])]
        
        try:
            if p_ids:
                execute_with_retry(models, DB, uid, used_pwd, 'product.template', 'write', [[p_ids[0]], vals])
            else:
                execute_with_retry(models, DB, uid, used_pwd, 'product.template', 'create', [vals])
        except Exception:
            vals.pop('pos_categ_ids', None)
            if cat_id:
                vals['pos_categ_id'] = cat_id
            if p_ids:
                execute_with_retry(models, DB, uid, used_pwd, 'product.template', 'write', [[p_ids[0]], vals])
            else:
                execute_with_retry(models, DB, uid, used_pwd, 'product.template', 'create', [vals])
        
        print(f"[{idx}/{len(MENU_ITEMS)}] {item['name']} - Rs. {item['price']} ({item['category']})", flush=True)
        success += 1
        time.sleep(0.1)

    print(f"\nAll {success} products added to POS successfully!", flush=True)
    print("Refresh your POS browser tab (Ctrl + F5).", flush=True)

if __name__ == '__main__':
    run()
