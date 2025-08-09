import logging
import os
import uuid
import random
from firebase_admin import credentials, db, initialize_app
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)

# --- Configuration ---
# You MUST replace these with your own secure credentials.
FIREBASE_CREDENTIALS_PATH = 'firebase-service-account-key.json'
FIREBASE_DATABASE_URL = "https://chat-now-38351-default-rtdb.firebaseio.com"
TELEGRAM_BOT_TOKEN = "8469240517:AAEpIlX0PbsC0c9hyItfmQzSGbgth1A050Y"
ADMIN_USER_ID = 7142274690  # Replace with your actual Telegram user ID

# --- Conversation States ---
# These states are for the admin panel's ConversationHandler.
ADMIN_MENU, PRODUCT_ACTION, OFFER_ACTION, EDIT_PRODUCT, EDIT_OFFER, DELETE_CONFIRM = range(6)
ADD_PRODUCT_NAME, ADD_PRODUCT_DESC, ADD_PRODUCT_PRICE, ADD_PRODUCT_IMAGE, ADD_PRODUCT_LINK = range(6, 11)
ADD_OFFER_TITLE, ADD_OFFER_DESC, ADD_OFFER_IMAGE, ADD_OFFER_LINK = range(11, 15)

# --- Firebase Initialization ---
def init_firebase():
    """Initializes the Firebase app."""
    try:
        if os.path.exists(FIREBASE_CREDENTIALS_PATH):
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL})
            logging.info("Firebase app initialized successfully.")
            return True
        else:
            logging.error(f"Firebase credentials file not found at: {FIREBASE_CREDENTIALS_PATH}")
            return False
    except Exception as e:
        logging.error(f"Failed to initialize Firebase: {e}")
        return False

# --- General Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a friendly welcome message when the /start command is issued."""
    user_name = update.effective_user.first_name
    welcome_message = (
        f"Hey there, {user_name}! 👋\n\n"
        "I'm a bot designed to help you find products and discover amazing offers. "
        "Just send me the name of the product you're looking for, or use "
        "the command /offers to see the latest deals! 🛒✨"
    )
    await update.message.reply_text(welcome_message)
    await update.message.reply_animation('https://media.giphy.com/media/3o7TKM85r3A5sQ1K7u/giphy.gif')

async def get_offers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and sends the latest offers from the database."""
    await update.message.reply_text("Grabbing the latest offers for you! 🤩")
    
    try:
        ref = db.reference('offers')
        all_offers = ref.get()
        
        if all_offers:
            for offer_id, offer in all_offers.items():
                image_url = offer.get('image_url', '')
                title = offer.get('title', 'Special Offer!')
                description = offer.get('description', 'No details available.')
                link = offer.get('link', '')

                keyboard = [[InlineKeyboardButton("🔥 Claim Offer", url=link)]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                caption_text = (
                    f"✨ **{title}** ✨\n\n"
                    f"**Details:** {description}"
                )
                
                await update.message.reply_photo(
                    photo=image_url,
                    caption=caption_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            await update.message.reply_animation('https://media.giphy.com/media/xT39C1H4J9UaQ/giphy.gif')
        else:
            await update.message.reply_text("Sorry, there are no active offers right now. Check back later! 😉")
    
    except Exception as e:
        logging.error(f"An error occurred fetching offers: {e}")
        await update.message.reply_text("Couldn't retrieve the offers at the moment. Please try again. 🙏")

async def find_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Finds a product in the Firebase database and sends the details in groups and DMs."""
    if update.effective_chat.type not in ["private", "group", "supergroup"]:
        return
        
    product_name = update.message.text.lower()
    await update.message.reply_text(f"Searching for '{product_name}'... give me a second! 🕵️‍♀️🔍")

    try:
        ref = db.reference('products')
        all_products = ref.get()
        product_data = None
        
        if all_products:
            for key, value in all_products.items():
                if product_name in value.get('name', '').lower():
                    product_data = value
                    break

        if product_data:
            image_url = product_data.get('image_url', '')
            name = product_data.get('name', 'N/A')
            description = product_data.get('description', 'No description available.')
            price = product_data.get('price', 'N/A')
            buy_link = product_data.get('buy_link', 'https://example.com/default-buy-link')

            keyboard = [[InlineKeyboardButton("🛍️ Buy Now", url=buy_link)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            caption_text = (
                f"🎉 **Product Found!** 🎉\n\n"
                f"**Name:** {name}\n"
                f"**Description:** {description}\n"
                f"**Price:** ${price}"
            )
            
            await update.message.reply_photo(
                photo=image_url,
                caption=caption_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            await update.message.reply_animation('https://media.giphy.com/media/Svs4Q8B96E87s73t1q/giphy.gif')
        else:
            await update.message.reply_text(
                f"Sorry, I couldn't find any products related to '{product_name}'. 😔\n\n"
                "Please double-check the spelling or try another product name."
            )
            await update.message.reply_animation('https://media.giphy.com/media/l0Iyl5Q1nO670T808/giphy.gif')
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        await update.message.reply_text("Oops! Something went wrong while searching. Please try again later. 😅")

# --- Admin Panel Handlers ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Shows the main admin menu."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to use this command. 🚫")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("Products 📦", callback_data='products')],
        [InlineKeyboardButton("Offers 🎁", callback_data='offers')],
        [InlineKeyboardButton("🚫 Exit Admin Panel", callback_data='exit')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to the Admin Panel! Please choose an option:", reply_markup=reply_markup)
    return ADMIN_MENU

async def handle_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the selection from the main admin menu."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'products':
        keyboard = [
            [InlineKeyboardButton("➕ Add Product", callback_data='add_product')],
            [InlineKeyboardButton("✏️ Edit Product", callback_data='edit_product')],
            [InlineKeyboardButton("🗑️ Delete Product", callback_data='delete_product')],
            [InlineKeyboardButton("⬅️ Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Products menu. What would you like to do?", reply_markup=reply_markup)
        return PRODUCT_ACTION
    elif query.data == 'offers':
        keyboard = [
            [InlineKeyboardButton("➕ Add Offer", callback_data='add_offer')],
            [InlineKeyboardButton("✏️ Edit Offer", callback_data='edit_offer')],
            [InlineKeyboardButton("🗑️ Delete Offer", callback_data='delete_offer')],
            [InlineKeyboardButton("⬅️ Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Offers menu. What would you like to do?", reply_markup=reply_markup)
        return OFFER_ACTION
    elif query.data == 'exit':
        await query.edit_message_text("Exiting Admin Panel. Goodbye! 👋")
        return ConversationHandler.END
    
    return ADMIN_MENU

async def handle_product_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles actions for products (add, edit, delete)."""
    query = update.callback_query
    await query.answer()

    if query.data == 'add_product':
        await query.edit_message_text("Please send the **name** of the new product.")
        return ADD_PRODUCT_NAME
    elif query.data == 'edit_product':
        await query.edit_message_text("Please send the **name** of the product you want to edit.")
        return EDIT_PRODUCT
    elif query.data == 'delete_product':
        await query.edit_message_text("Please send the **name** of the product you want to delete.")
        return DELETE_CONFIRM
    elif query.data == 'back':
        return await admin_panel(update, context)
        
    return PRODUCT_ACTION

async def handle_offer_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles actions for offers (add, edit, delete)."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'add_offer':
        await query.edit_message_text("Please send the **title** of the new offer.")
        return ADD_OFFER_TITLE
    elif query.data == 'edit_offer':
        await query.edit_message_text("Please send the **title** of the offer you want to edit.")
        return EDIT_OFFER
    elif query.data == 'delete_offer':
        await query.edit_message_text("Please send the **title** of the offer you want to delete.")
        return DELETE_CONFIRM
    elif query.data == 'back':
        return await admin_panel(update, context)

    return OFFER_ACTION
    
async def handle_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirms and deletes a product or offer."""
    item_name = update.message.text
    ref_products = db.reference('products')
    ref_offers = db.reference('offers')
    item_type = context.user_data.get('delete_item_type')

    if item_type == 'product':
        ref = ref_products
    elif item_type == 'offer':
        ref = ref_offers
    else:
        await update.message.reply_text("Error: Item type not specified. Please try again.")
        return ConversationHandler.END
    
    all_items = ref.get()
    item_key = None
    
    if all_items:
        for key, value in all_items.items():
            if value.get('name', '').lower() == item_name.lower() or value.get('title', '').lower() == item_name.lower():
                item_key = key
                break
    
    if item_key:
        ref.child(item_key).delete()
        await update.message.reply_text(f"✅ The item '{item_name}' has been successfully deleted!")
    else:
        await update.message.reply_text(f"❌ Could not find an item named '{item_name}'. No deletion was performed.")
        
    return ConversationHandler.END

# --- Add Product Conversation ---
async def get_add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the product name and asks for the description."""
    context.user_data['new_item_data'] = {'name': update.message.text}
    await update.message.reply_text("Great! Now, send the product **description**.")
    return ADD_PRODUCT_DESC

async def get_add_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the product description and asks for the price."""
    context.user_data['new_item_data']['description'] = update.message.text
    await update.message.reply_text("Got it. Now, send the product **price** (e.g., 99.99).")
    return ADD_PRODUCT_PRICE

async def get_add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the product price and asks for the image URL."""
    context.user_data['new_item_data']['price'] = update.message.text
    await update.message.reply_text("Perfect. Now, send the **image URL** for the product.")
    return ADD_PRODUCT_IMAGE

async def get_add_product_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the image URL and asks for the buy link."""
    context.user_data['new_item_data']['image_url'] = update.message.text
    await update.message.reply_text("Almost done! Please send the product's **buy link**.")
    return ADD_PRODUCT_LINK

async def get_add_product_link_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the final piece of info and saves the product to the database."""
    context.user_data['new_item_data']['buy_link'] = update.message.text
    
    item_data = context.user_data['new_item_data']
    ref = db.reference('products')
    
    try:
        new_item_ref = ref.push(item_data)
        await update.message.reply_text(
            f"✅ New product **'{item_data['name']}'** has been successfully added!\n"
            f"Database ID: {new_item_ref.key}",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"An error occurred while saving the product: {e}")
        logging.error(f"Error saving product to Firebase: {e}")
    
    context.user_data.clear()
    return ConversationHandler.END

# --- Add Offer Conversation ---
async def get_add_offer_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the offer title and asks for the description."""
    context.user_data['new_item_data'] = {'title': update.message.text}
    await update.message.reply_text("Now, send the offer's **description**.")
    return ADD_OFFER_DESC

async def get_add_offer_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the offer description and asks for the image URL."""
    context.user_data['new_item_data']['description'] = update.message.text
    await update.message.reply_text("Great! Now send the **image URL** for the offer.")
    return ADD_OFFER_IMAGE

async def get_add_offer_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the image URL and asks for the offer link."""
    context.user_data['new_item_data']['image_url'] = update.message.text
    await update.message.reply_text("Almost there! Please send the **link** for the offer.")
    return ADD_OFFER_LINK

async def get_add_offer_link_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the final piece of info and saves the offer to the database."""
    context.user_data['new_item_data']['link'] = update.message.text
    
    item_data = context.user_data['new_item_data']
    ref = db.reference('offers')
    
    try:
        new_item_ref = ref.push(item_data)
        await update.message.reply_text(
            f"✅ New offer **'{item_data['title']}'** has been successfully added!\n"
            f"Database ID: {new_item_ref.key}",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"An error occurred while saving the offer: {e}")
        logging.error(f"Error saving offer to Firebase: {e}")

    context.user_data.clear()
    return ConversationHandler.END

# --- General Utility Handlers ---
async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the current conversation and ends it."""
    await update.message.reply_text('Operation cancelled. You can start a new command anytime.')
    context.user_data.clear()
    return ConversationHandler.END

async def invalid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles invalid commands in conversation."""
    await update.message.reply_text("I didn't understand that. Please provide the requested information or use /cancel to exit.")

# --- Main Bot Function ---
def main() -> None:
    """Starts the bot."""
    if not init_firebase():
        return
        
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation handler for the admin panel
    admin_conversation = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={
            ADMIN_MENU: [CallbackQueryHandler(handle_admin_menu, pattern='^products$|^offers$|^exit$')],
            PRODUCT_ACTION: [
                CallbackQueryHandler(handle_product_action, pattern='^add_product$|^edit_product$|^delete_product$|^back$'),
            ],
            OFFER_ACTION: [
                CallbackQueryHandler(handle_offer_action, pattern='^add_offer$|^edit_offer$|^delete_offer$|^back$'),
            ],
            ADD_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_add_product_name)],
            ADD_PRODUCT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_add_product_desc)],
            ADD_PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_add_product_price)],
            ADD_PRODUCT_IMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_add_product_image)],
            ADD_PRODUCT_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_add_product_link_and_save)],
            ADD_OFFER_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_add_offer_title)],
            ADD_OFFER_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_add_offer_desc)],
            ADD_OFFER_IMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_add_offer_image)],
            ADD_OFFER_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_add_offer_link_and_save)],
            DELETE_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_delete_confirm)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)],
        allow_reentry=True,
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("offers", get_offers))
    application.add_handler(admin_conversation)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, find_product))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
    main()