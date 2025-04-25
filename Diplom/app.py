# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
from decimal import Decimal
from collections import defaultdict
from calendar import monthrange

from Diplom.config import config
from Diplom.models import db, User, Category, Transaction, Budget
from Diplom.forms import RegistrationForm
from Diplom.utils import analyze_expenses_by_category

from flask_migrate import Migrate

# --- ИНИЦИАЛИЗАЦИЯ ---
app = Flask(__name__)
app.config.from_object(config)
CORS(app)

# Инициализируем БД и миграции
db.init_app(app)
migrate = Migrate(app, db)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ======================== ГЛАВНАЯ СТРАНИЦА ========================
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

# ======================== АНАЛИТИКА ========================
@app.route('/analytics')
@login_required
def analytics():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    expenses_by_category = defaultdict(float)

    for t in transactions:
        if not t.category.is_income:
            expenses_by_category[t.category.name] += float(t.amount)

    labels = list(expenses_by_category.keys())
    values = list(expenses_by_category.values())

    return render_template('analytics.html', labels=labels, values=values)

# ======================== БЮДЖЕТ ========================
@app.route('/budget')
@login_required
def budget():
    categories = Category.query.filter_by(user_id=current_user.id).all()
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()

    expenses_by_category = defaultdict(float)
    for t in transactions:
        if not t.category.is_income:
            expenses_by_category[t.category_id] += float(t.amount)

    budget_info = []
    for b in budgets:
        spent = expenses_by_category.get(b.category_id, 0)
        exceeded = spent > float(b.amount)
        budget_info.append({
            'category': b.category.name,
            'amount': float(b.amount),
            'spent': spent,
            'exceeded': exceeded
        })

    return render_template('budget.html', categories=categories, budgets=budget_info)

@app.route('/set_budget', methods=['POST'])
@login_required
def set_budget():
    category_id = request.form.get('category_id')
    limit = request.form.get('limit')

    today = date.today()
    year = today.year
    month = today.month
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    budget = Budget(
        user_id=current_user.id,
        category_id=int(category_id),
        amount=Decimal(limit),
        start_date=first_day,
        end_date=last_day
    )
    db.session.add(budget)
    db.session.commit()
    flash("Бюджет установлен", "success")
    return redirect(url_for('budget'))

# ======================== СОВЕТЫ ========================
@app.route('/tips')
@login_required
def tips():
    return render_template('tips.html')

# ======================== РЕГИСТРАЦИЯ ========================
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email уже используется', 'danger')
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Регистрация прошла успешно! Теперь войдите.', 'success')
            return redirect(url_for('login'))
    return render_template('auth.html', form=form)

# ======================== ЛОГИН ========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = RegistrationForm()
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('auth.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# ======================== ДАШБОРД ========================
@app.route('/dashboard')
@login_required
def dashboard():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.transaction_date).all()

    incomes_by_date = defaultdict(float)
    expenses_by_date = defaultdict(float)

    for t in transactions:
        date_str = t.transaction_date.strftime('%Y-%m-%d')
        if t.category.is_income:
            incomes_by_date[date_str] += float(t.amount)
        else:
            expenses_by_date[date_str] += float(t.amount)

    all_dates = sorted(set(incomes_by_date.keys()) | set(expenses_by_date.keys()))

    chart_data = {
        'labels': all_dates,
        'incomes': [incomes_by_date.get(date, 0) for date in all_dates],
        'expenses': [expenses_by_date.get(date, 0) for date in all_dates],
    }

    incomes = sum(chart_data['incomes'])
    expenses = sum(chart_data['expenses'])
    balance = incomes - expenses

    return render_template(
        'dashboard.html',
        transactions=transactions[-5:][::-1],
        chart_data=chart_data,
        incomes=incomes,
        expenses=expenses,
        balance=balance
    )

# ======================== ТРАНЗАКЦИИ ========================
@app.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    q = request.args.get('q')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Transaction.query.filter_by(user_id=current_user.id)

    if q:
        query = query.join(Category).filter(
            Category.name.ilike(f'%{q}%') |
            Transaction.description.ilike(f'%{q}%')
        )

    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)

    transactions = query.order_by(Transaction.transaction_date.desc()).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('transactions.html', transactions=transactions, categories=categories)

@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    category_id = request.form.get('category_id')
    amount = request.form.get('amount')
    description = request.form.get('description')
    transaction_date = request.form.get('transaction_date')

    if not category_id or not amount or not transaction_date:
        flash('Все поля, кроме описания, обязательны', 'danger')
        return redirect(url_for('get_transactions'))

    try:
        new_transaction = Transaction(
            user_id=current_user.id,
            category_id=int(category_id),
            amount=Decimal(amount),
            description=description,
            transaction_date=date.fromisoformat(transaction_date)
        )
        db.session.add(new_transaction)
        db.session.commit()
        flash('Транзакция добавлена!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {e}', 'danger')

    return redirect(url_for('get_transactions'))

# ======================== КАТЕГОРИИ ========================
@app.route('/categories', methods=['GET'])
@login_required
def get_categories():
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('categories.html', categories=categories)

@app.route('/add_category', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name')
    description = request.form.get('description')
    is_income = request.form.get('is_income') == 'on'

    if not name:
        flash("Название категории обязательно", "danger")
        return redirect(url_for('get_categories'))

    new_category = Category(
        user_id=current_user.id,
        name=name,
        description=description,
        is_income=is_income
    )
    db.session.add(new_category)
    db.session.commit()
    flash("Категория добавлена!", "success")
    return redirect(url_for('get_categories'))

@app.route('/delete_category/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)

    if category.user_id != current_user.id:
        flash("У вас нет доступа к этой категории", "danger")
        return redirect(url_for('get_categories'))

    db.session.delete(category)
    db.session.commit()
    flash("Категория удалена", "success")
    return redirect(url_for('get_categories'))

# ======================== СТАРТ ПРИЛОЖЕНИЯ ========================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
