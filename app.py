from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
import mysql.connector
import random

app = Flask(__name__)
app.secret_key = 'b1e2c3d4a5f67890123456789abcdef'

# MySQL Configuration
db = mysql.connector.connect(
    host='localhost',
    user='root',  # Your MySQL username
    password='Gaurav@123*',  # Your MySQL password
    database='iphone_parts_order'
)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        password = request.form['password']
        otp = request.form['otp']

        if 'otp' in session and int(otp) == session['otp']:
            cursor = db.cursor()
            cursor.execute("INSERT INTO users (name, phone, password) VALUES (%s, %s, %s)", (name, phone, password))
            db.commit()
            cursor.close()
            flash('Account created successfully!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
            return render_template('signup.html')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']

        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE phone=%s AND password=%s", (phone, password))
        user = cursor.fetchone()
        cursor.close()

        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]  # Store user's name in session
            session['phone'] = user[2]

            # Retrieve cart from database
            cursor = db.cursor()
            cursor.execute("SELECT part_name, quantity, color FROM user_cart WHERE user_id=%s", (user[0],))
            cart_items = cursor.fetchall()
            session['cart'] = {}
            for item in cart_items:
                part_name = item[0]
                quantity = item[1]
                color = item[2]
                item_key = f"{part_name}_{color}" if color != 'none' else part_name
                session['cart'][item_key] = {
                    'part': part_name,
                    'quantity': quantity,
                    'color': color,
                    'price': prices.get(part_name, 0)  # Ensure price is set
                }
            cursor.close()

            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid phone number or password. Please try again.', 'error')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    phone = data.get('phone')

    cursor = db.cursor()
    cursor.execute("SELECT password FROM users WHERE phone=%s", (phone,))
    user = cursor.fetchone()
    cursor.close()

    if user:
        return jsonify(success=True, password=user[0])
    else:
        return jsonify(success=False, message='Phone number not found.')

@app.route('/initiate_otp', methods=['POST'])
def initiate_otp():
    data = request.get_json()
    phone = data.get('phone')
    
    # Ensure the phone number is in E.164 format
    if not phone.startswith("+"):
        phone = "+91" + phone
    
    print(f"Formatted phone number: {phone}")  # Debug statement

    # Generate and send OTP
    otp = generate_otp()  # Your OTP generation logic
    session['otp'] = otp
    session['phone'] = phone
    send_sms(phone, f'Your OTP is {otp}')

    return jsonify(success=True)

@app.route('/verify_user_otp', methods=['POST'])
def verify_user_otp():
    data = request.get_json()
    phone = data.get('phone')
    entered_otp = data.get('otp')
    
    # Ensure the phone number is in E.164 format
    if not phone.startswith("+"):
        phone = "+91" + phone

    print(f"Formatted phone number for verification: {phone}")  # Debug statement

    if 'otp' in session and int(entered_otp) == session['otp']:
        phone_db = phone.lstrip("+91")  # Remove +91 prefix for database comparison
        cursor = db.cursor()
        cursor.execute("SELECT password FROM users WHERE phone=%s", (phone_db,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            return jsonify(success=True, password=user[0])
        else:
            return jsonify(success=False, message='Phone number not found.')
    else:
        return jsonify(success=False, message='Invalid OTP.')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('home'))


@app.route('/orders')
def orders():
    if 'user_id' not in session:
        flash('Please log in to view your orders.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor = db.cursor()
    cursor.execute("SELECT * FROM orders WHERE user_id = %s", (user_id,))
    orders = cursor.fetchall()
    cursor.close()

    return render_template('orders.html', orders=orders)


# Function to send signup OTP
def sendSignupOTP():
    phone = request.form['phone']
    otp = generate_otp()
    session['otp'] = otp

    send_sms(phone, f"Your OTP for signup is: {otp}")
    flash('OTP sent successfully!', 'success')

def generate_otp():
    return random.randint(100000, 999999)

def send_sms(phone_number, message):
    client = Client(twilio_account_sid, twilio_auth_token)
    try:
        client.messages.create(
            body=message,
            from_=twilio_phone_number,
            to=phone_number
        )
        print("SMS sent successfully!")
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        
@app.route('/send_signup_otp', methods=['POST'])
def send_signup_otp():
    data = request.get_json()
    print("Received data:", data)

    if not data:
        return "No data received", 400

    phone = data.get('phone')
    print("Phone number for OTP:", phone)

    if not phone:
        return "Phone number missing", 400

    otp = generate_otp()
    session['otp'] = otp
    print("Generated OTP:", otp)

    try:
        send_sms(phone, f"Your OTP for signup is: {otp}")
        print("OTP sent successfully!")
        return 'OTP sent successfully!'
    except Exception as e:
        print(f"Failed to send OTP: {e}")
        return str(e), 500




# Twilio Configuration
twilio_account_sid = 'ACb941e0963925ff38ffa131e6258ba0e9'
twilio_auth_token = 'c83822a9f767d7d39f570ab5fde23d16'
twilio_phone_number = '+16502970662'

# Function to generate OTP
def generate_otp():
    return random.randint(100000, 999999)

@app.route('/')
@app.route('/home', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        session['model'] = request.form['model']
        return redirect(url_for('parts'))
    
    user_initials = session.get('user_name', '')[:2].upper() if 'user_name' in session else None
    return render_template('home.html', user_initials=user_initials)


import pandas as pd
import requests
from io import StringIO

GOOGLE_SHEET_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vScuIlO9v1Si_ly4FnDhKzqIKiqy_AFDrB191U__KnWaCHzvn-fatel1Z1n_feM2aozZV6sr1pohiHk/pub?output=csv"

@app.route('/parts', methods=['GET', 'POST'])
def parts():
    if 'cart' not in session:
        session['cart'] = {}

    # The model user selected (e.g., "iPhone 12 Pro Max")
    iphone_model = session.get('model', 'iPhone 11')

    # --- Load data from Google Sheet ---
    try:
        response = requests.get(GOOGLE_SHEET_CSV)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))

        # Clean column headers
        df.columns = df.columns.str.strip()
        model_col = iphone_model.replace("iPhone ", "").strip()  # Example: "iPhone 12 Pro" → "12 Pro"

        # Try to find the closest matching model column
        available_cols = [c.lower() for c in df.columns]
        model_match = None
        for col in df.columns:
            if model_col.lower() in col.lower():
                model_match = col
                break

        if model_match is None:
            raise KeyError(f"No matching column for {iphone_model}")

        # Build parts + descriptions
        available_parts = dict(zip(df["Part Name"], df["Info"]))

        # Build price dictionary for this model
        prices = dict(zip(df["Part Name"], df[model_match]))

    except Exception as e:
        print("Error loading parts from Google Sheet:", e)
        available_parts = {}
        prices = {}

    # --- Search filter (for user queries) ---
    if request.method == 'GET' and 'query' in request.args:
        query = request.args.get('query', '').lower()
        filtered_parts = {
            key: value for key, value in available_parts.items()
            if query in key.lower() or query in value.lower()
        }
        return render_template('parts.html',
                            parts=filtered_parts,
                            prices=prices,
                            cart=session['cart'],
                            iphone_model=iphone_model)

    # --- Add items to cart (POST) ---
    if request.method == 'POST':
        user_id = session.get('user_id')
        parts_with_colors = [
            "Back Glass", "SIM Tray", "LCD Screen", "Charging Port",
            "Home Button", "Power Button", "Volume Button",
            "Camera Lens Cover", "Digitizer", "Battery Connector"
        ]

        for part in request.form:
            if part.startswith('quantity_'):
                quantity_key = part
                part_name = part.replace('quantity_', '')
                quantities = request.form.getlist(quantity_key)
                colors = request.form.getlist(f'color_{part_name}') if part_name in parts_with_colors else ['none'] * len(quantities)

                for quantity, color in zip(quantities, colors):
                    if int(quantity) > 0:
                        item_key = f"{part_name}_{color}" if color != 'none' else part_name
                        if item_key in session['cart']:
                            session['cart'][item_key]['quantity'] += int(quantity)
                        else:
                            price = prices.get(part_name, 0)
                            session['cart'][item_key] = {
                                'part': part_name,
                                'quantity': int(quantity),
                                'color': color,
                                'price': price,
                                'iphone_model': iphone_model
                            }

        session.modified = True
        flash('Items added to cart successfully!', 'success')
        return redirect(url_for('view_cart'))

    # --- Render parts list ---
    return render_template('parts.html',
                        parts=available_parts,
                        prices=prices,
                        cart=session['cart'],
                        iphone_model=iphone_model)




@app.route('/add_all_to_cart', methods=['POST'])
def add_all_to_cart():
    if 'user_id' not in session:
        flash('Please log in to add items to your cart.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    if not user_id:
        flash('User ID not found. Please log in again.', 'error')
        return redirect(url_for('login'))

    if 'cart' not in session:
        session['cart'] = {}

    iphone_model = session.get('model', 'Unknown')
    parts_with_colors = ["Back Glass", "SIM Tray", "LCD Screen", "Charging Port", "Home Button", "Power Button", "Volume Button", "Camera Lens Cover", "Digitizer", "Battery Connector"]

    for part in request.form:
        if part.startswith('quantity_'):
            quantity_key = part
            part_name = part.replace('quantity_', '')

            quantities = request.form.getlist(quantity_key)
            colors = request.form.getlist(f'color_{part_name}') if part_name in parts_with_colors else ['none'] * len(quantities)

            for quantity, color in zip(quantities, colors):
                if int(quantity) > 0:
                    item_key = f"{part_name}_{color}" if color != 'none' else part_name
                    if item_key in session['cart']:
                        session['cart'][item_key]['quantity'] += int(quantity)
                    else:
                        session['cart'][item_key] = {
                            'part': part_name,
                            'quantity': int(quantity),
                            'color': color,
                            'price': prices.get(part_name, 0),
                            'iphone_model': iphone_model
                        }

                    # Save to database
                    cursor = db.cursor()
                    cursor.execute("""
                        INSERT INTO user_cart (user_id, part_name, quantity, color, iphone_model) 
                        VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE quantity=quantity + %s
                    """, (user_id, part_name, int(quantity), color, iphone_model, int(quantity)))
                    db.commit()

    cursor.close()
    session.modified = True
    flash('Items added to cart successfully!', 'success')
    return redirect(url_for('view_cart'))


@app.route('/cart', methods=['GET', 'POST'])
def view_cart():
    if 'user_id' not in session:
        flash('Please log in to view your cart.', 'error')
        return redirect(url_for('login'))

    if 'cart' not in session:
        session['cart'] = {}

    user_id = session.get('user_id')
    if not user_id:
        flash('User ID not found. Please log in again.', 'error')
        return redirect(url_for('login'))

    iphone_model = session.get('model', 'Unknown')

    if request.method == 'POST':
        # Update quantities
        for item_key, item in list(session['cart'].items()):
            quantity = int(request.form.get(f'quantity_{item_key}', 0))
            if quantity > 0:
                session['cart'][item_key]['quantity'] = quantity

                # Ensure the item has the iphone_model key
                if 'iphone_model' not in item:
                    item['iphone_model'] = iphone_model
                
                # Update database
                part_name, color = item_key.split('_') if '_' in item_key else (item_key, 'none')
                cursor = db.cursor()
                cursor.execute("""
                    UPDATE user_cart SET quantity=%s WHERE user_id=%s AND part_name=%s AND color=%s AND iphone_model=%s
                """, (quantity, user_id, part_name, color, item['iphone_model']))
                db.commit()
                cursor.close()
            else:
                # Remove from session and database
                part_name, color = item_key.split('_') if '_' in item_key else (item_key, 'none')
                session['cart'].pop(item_key)

                cursor = db.cursor()
                cursor.execute("""
                    DELETE FROM user_cart WHERE user_id=%s AND part_name=%s AND color=%s AND iphone_model=%s
                """, (user_id, part_name, color, item.get('iphone_model', iphone_model)))
                db.commit()
                cursor.close()

        # Handle empty cart button
        if 'empty_cart' in request.form:
            session['cart'] = {}
            cursor = db.cursor()
            cursor.execute("DELETE FROM user_cart WHERE user_id=%s", (user_id,))
            db.commit()
            cursor.close()

        session.modified = True

    # Filter parts to only include color fields for specific items
    parts_with_colors = ["Back Glass", "SIM Tray", "LCD Screen", "Charging Port", "Home Button", "Power Button", "Volume Button", "Camera Lens Cover", "Digitizer", "Battery Connector"]
    display_cart = {}
    for key, item in session['cart'].items():
        if key.split('_')[0] in parts_with_colors:
            display_cart[key] = item
        else:
            item = {k: v for k, v in item.items() if k != 'color'}
            display_cart[key] = item

    # Calculate total price using the 'price' attribute, handle missing prices gracefully
    total_price = sum(item.get('price', 0) * item.get('quantity', 0) for item in display_cart.values())

    print(f"Cart Items: {display_cart}")  # Debug statement
    return render_template('cart.html', cart=display_cart, total_price=total_price, iphone_model=iphone_model)


@app.route('/purchase', methods=['POST'])
def purchase():
    if 'user_id' not in session:
        flash('Please log in to complete your purchase.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    items = session.get('cart', [])

    if not items:
        flash('Your cart is empty.', 'error')
        return redirect(url_for('view_cart'))

    cursor = db.cursor()
    for item in items:
        cursor.execute(
            "INSERT INTO cart (user_id, item_name, color, quantity, price) VALUES (%s, %s, %s, %s, %s)",
            (user_id, item['part'], item['color'], item['quantity'], prices[item['part']])
        )
        print(f'Inserted into DB: {item}')  # Debug statement
    db.commit()
    cursor.close()

    # Clear the cart after purchase
    session['cart'] = []
    session.modified = True

    flash('Purchase completed successfully!', 'success')
    return redirect(url_for('view_cart'))



@app.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.json
    phone = data.get('phone')
    if not phone.startswith("+91"):
        phone = "+91" + phone
    otp = generate_otp()
    session['otp'] = otp

    send_sms(phone, f"Your OTP for order confirmation is: {otp}")
    return "OTP sent", 200

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        user_name = request.form['name']
        entered_otp = request.form['otp']
        if not phone.startswith("+91"):
            phone = "+91" + phone

        if 'otp' in session and int(entered_otp) == session['otp']:
            # OTP is correct, proceed with order confirmation
            total_price = 0
            order_details = []
            user_id = session.get('user_id')
            iphone_model = session.get('model', 'Unknown')

            for item_key, item in session['cart'].items():
                part_name = item_key.split('_')[0]
                quantity = item['quantity']

                # Fetch part name and price from product_prices table
                cursor = db.cursor()
                cursor.execute("""
                    SELECT part_name, price FROM product_prices WHERE part_name=%s AND iphone_model=%s
                """, (part_name, iphone_model))
                product_row = cursor.fetchone()
                
                part_name, price = product_row if product_row else (None, 0)
                total_price += price * quantity
                order_details.append(f"{part_name} (Color: {item.get('color', 'N/A')}): {quantity} x {price}")

            order_details_str = "\n".join(order_details)
            order_id = f"ORDER{len(session['cart'])}{sum(item['quantity'] for item in session['cart'].values())}"

            try:
                cursor.execute("""
                    INSERT INTO orders (order_id, user_id, user_name, email, phone, address, iphone_model, total_price, order_details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (order_id, user_id, user_name, email, phone, address, iphone_model, total_price, order_details_str))
                db.commit()
                cursor.close()
                print("Order data stored successfully in the database!")

                # Clear cart entries from the database
                cursor = db.cursor()
                cursor.execute("DELETE FROM user_cart WHERE user_id=%s", (user_id,))
                db.commit()
                cursor.close()

            except Exception as e:
                print(f"Failed to store order data in the database: {e}")

            send_sms(phone, f"Thank you for your order! Order ID: {order_id}, Total Price: ₹{total_price}")
            send_email_to_distributor("gauravchudasama333@gmail.com", order_id, user_name, phone, address, iphone_model, total_price, order_details_str)
            session['cart'] = {}
            session.modified = True
            return render_template('order_confirmation.html', order_id=order_id, total_price=total_price)
        else:
            error = "Invalid OTP. Please try again."
            total_price = sum(prices.get(part.split('_')[0], 0) * item['quantity'] for part, item in session['cart'].items())
            return render_template('checkout.html', error=error, cart=session['cart'], total_price=total_price)

    total_price = sum(prices.get(part.split('_')[0], 0) * item['quantity'] for part, item in session['cart'].items())
    return render_template('checkout.html', error=error, cart=session['cart'], total_price=total_price)



def send_sms(phone_number, message):
    client = Client(twilio_account_sid, twilio_auth_token)
    try:
        client.messages.create(
            body=message,
            from_=twilio_phone_number,
            to=phone_number
        )
        print("SMS sent successfully!")
    except Exception as e:
        print(f"Failed to send SMS: {e}")

def send_email_to_distributor(to_email, order_id, user_name, user_phone, user_address, iphone_model, total_price, order_details):
    # SMTP Configuration for Elastic Email
    sender_email = "gauravchudasama333@gmail.com"
    sender_password = "8BC6070B0EDDCB13A9B7C1D4F338D4B0B21E"
    smtp_host = "smtp.elasticemail.com"
    smtp_port = 2525

    subject = "New Order Received"
    body = (f"A new order has been placed!\n\n"
            f"Order ID: {order_id}\n"
            f"Name: {user_name}\n"
            f"Phone: {user_phone}\n"
            f"Address: {user_address}\n"
            f"iPhone Model: {iphone_model}\n"
            f"Total Price: ₹{total_price}\n"
            f"Order Details:\n{order_details}\n\n"
            "Please process the order as soon as possible.")

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        print("Email sent successfully to distributor!")
    except Exception as e:
        print(f"Failed to send email to distributor: {e}")

if __name__ == '__main__':
    app.run(debug=True)

#E:\fyp\.venv\Scripts\python.exe e:\fyp\app.py
