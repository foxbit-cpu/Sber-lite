import json
import os
from datetime import datetime, date
import tkinter as tk
from tkinter import ttk, messagebox
from random import randint

# ----------------------------------------------------------------------
# Класс транзакции
# ----------------------------------------------------------------------
class Transaction:
    def __init__(self, amount: float, category: str, description: str,
                 trans_type: str, date_str: str = None):
        self.amount = amount
        self.category = category
        self.description = description
        self.type = trans_type.lower()  # 'income' или 'expense'
        if date_str:
            self.date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            self.date = date.today()

    def to_dict(self) -> dict:
        return {
            "amount": self.amount,
            "category": self.category,
            "description": self.description,
            "type": self.type,
            "date": self.date.strftime("%Y-%m-%d")
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            amount=data["amount"],
            category=data["category"],
            description=data["description"],
            trans_type=data["type"],
            date_str=data["date"]
        )


# ----------------------------------------------------------------------
# Класс одного счёта
# ----------------------------------------------------------------------
class Account:
    def __init__(self, name: str, initial_balance: float = 0.0):
        self.name = name
        self.balance = initial_balance
        self.transactions: list[Transaction] = []

    def add_transaction(self, t: Transaction):
        self.transactions.append(t)
        if t.type == "income":
            self.balance += t.amount
        else:
            self.balance -= t.amount

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "balance": self.balance,
            "transactions": [t.to_dict() for t in self.transactions]
        }

    @classmethod
    def from_dict(cls, data: dict):
        acc = cls(data["name"], data["balance"])
        acc.transactions = [Transaction.from_dict(td) for td in data["transactions"]]
        return acc


# ----------------------------------------------------------------------
# Класс банка (управляет счетами и общими лимитами)
# ----------------------------------------------------------------------
class Bank:
    def __init__(self):
        self.accounts: list[Account] = []
        self.limits: dict[str, float] = {}

    def add_account(self, name: str, initial_balance: float = 0.0):
        if any(acc.name == name for acc in self.accounts):
            raise ValueError(f"Счёт с именем '{name}' уже существует")
        self.accounts.append(Account(name, initial_balance))

    def get_account(self, name: str) -> Account:
        for acc in self.accounts:
            if acc.name == name:
                return acc
        raise ValueError(f"Счёт '{name}' не найден")

    def add_transaction(self, account_name: str, t: Transaction):
        acc = self.get_account(account_name)
        acc.add_transaction(t)
        self._check_limit(t)

    def _check_limit(self, t: Transaction):
        if t.type != "expense" or t.category not in self.limits:
            return
        total = 0.0
        for acc in self.accounts:
            for tr in acc.transactions:
                if (tr.type == "expense" and tr.category == t.category and
                        tr.date.month == t.date.month and tr.date.year == t.date.year):
                    total += tr.amount
        if total > self.limits[t.category]:
            self.limit_exceeded = (t.category, total, self.limits[t.category])
        else:
            self.limit_exceeded = None

    def remove_account(self, account_name: str):
        acc = self.get_account(account_name)
        self.accounts.remove(acc)

    def remove_transaction(self, account_name: str, transaction: Transaction):
        acc = self.get_account(account_name)
        # Восстанавливаем баланс
        if transaction.type == "income":
            acc.balance -= transaction.amount
        else:
            acc.balance += transaction.amount
        acc.transactions.remove(transaction)

    def remove_limit(self, category: str):
        if category in self.limits:
            del self.limits[category]

    def report_period(self, start_date: date, end_date: date, account_name: str = None) -> tuple[float, float, dict[str, float]]:
        income = 0.0
        expense_by_cat = {}
        accounts = [self.get_account(account_name)] if account_name else self.accounts
        for acc in accounts:
            for t in acc.transactions:
                if start_date <= t.date <= end_date:
                    if t.type == "income":
                        income += t.amount
                    else:
                        expense_by_cat[t.category] = expense_by_cat.get(t.category, 0.0) + t.amount
        total_expense = sum(expense_by_cat.values())
        return income, total_expense, expense_by_cat

    def get_all_transactions(self, start_date=None, end_date=None, category=None, account_name=None) -> list[tuple[str, Transaction]]:
        result = []
        for acc in self.accounts:
            if account_name and acc.name != account_name:
                continue
            for t in acc.transactions:
                if start_date and t.date < start_date:
                    continue
                if end_date and t.date > end_date:
                    continue
                if category and t.category != category:
                    continue
                result.append((acc.name, t))
        return result

    def total_balance(self) -> float:
        return sum(acc.balance for acc in self.accounts)

    def set_limit(self, category: str, amount: float):
        self.limits[category] = amount

    def check_limits(self) -> list[str]:
        warnings = []
        today = date.today()
        for cat, limit in self.limits.items():
            total = 0.0
            for acc in self.accounts:
                for t in acc.transactions:
                    if (t.type == "expense" and t.category == cat and
                            t.date.month == today.month and t.date.year == today.year):
                        total += t.amount
            if total > limit:
                warnings.append(f"Категория '{cat}': {total:.2f} / {limit:.2f}")
        return warnings

    def to_dict(self) -> dict:
        return {
            "accounts": [acc.to_dict() for acc in self.accounts],
            "limits": self.limits
        }

    @classmethod
    def from_dict(cls, data: dict):
        bank = cls()
        bank.accounts = [Account.from_dict(acc_data) for acc_data in data["accounts"]]
        bank.limits = data.get("limits", {})
        return bank


# ----------------------------------------------------------------------
# Функции сохранения/загрузки
# ----------------------------------------------------------------------
DATA_FILE = "bank_data.json"

def save_data(bank: Bank):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(bank.to_dict(), f, ensure_ascii=False, indent=2)

def load_data() -> Bank:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Bank.from_dict(data)
    return Bank()


# ----------------------------------------------------------------------
# Вспомогательная функция для генерации случайного цвета
# ----------------------------------------------------------------------
def random_color():
    return "#{:06x}".format(randint(0, 0xFFFFFF))


# ----------------------------------------------------------------------
# Главный класс приложения
# ----------------------------------------------------------------------
class BankApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Банковское приложение")
        self.root.geometry("1200x800")

        self.bank = load_data()
        if not self.bank.accounts:
            self.bank.add_account("Наличные", 0.0)
            save_data(self.bank)

        self.limit_exceeded = None

        # Основной контейнер с вкладками
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Создание вкладок
        self.tab_main = ttk.Frame(self.notebook)
        self.tab_trans = ttk.Frame(self.notebook)
        self.tab_reports = ttk.Frame(self.notebook)
        self.tab_limits = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_main, text="🏠 Главная")
        self.notebook.add(self.tab_trans, text="💰 Транзакции")
        self.notebook.add(self.tab_reports, text="📊 Отчёты")
        self.notebook.add(self.tab_limits, text="⚡ Лимиты")

        # Инициализация вкладок
        self.setup_main_tab()
        self.setup_trans_tab()
        self.setup_reports_tab()
        self.setup_limits_tab()

        # Первоначальное обновление данных
        self.refresh_accounts_list()
        self.refresh_trans_list()
        self.refresh_limits_list()
        self.update_account_combos()

        # Статус бар
        self.status_bar = tk.Label(self.root, text="Готов к работе", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ------------------------------------------------------------------
    # Главная вкладка (Dashboard)
    # ------------------------------------------------------------------
    def setup_main_tab(self):
        frame = self.tab_main

        # Верхняя панель с общим балансом
        balance_frame = ttk.Frame(frame)
        balance_frame.pack(fill=tk.X, pady=10)

        self.total_balance_label = ttk.Label(
            balance_frame,
            text="",
            font=("Helvetica", 32, "bold")
        )
        self.total_balance_label.pack(pady=20)

        # Карточки счетов
        accounts_frame = ttk.LabelFrame(frame, text="Мои счета", padding=15)
        accounts_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Таблица счетов
        columns = ("name", "balance")
        self.accounts_tree = ttk.Treeview(
            accounts_frame,
            columns=columns,
            show="headings",
            height=6
        )
        self.accounts_tree.heading("name", text="Название счёта")
        self.accounts_tree.heading("balance", text="Баланс")

        self.accounts_tree.column("name", width=250)
        self.accounts_tree.column("balance", width=150)

        scrollbar = ttk.Scrollbar(accounts_frame, orient=tk.VERTICAL, command=self.accounts_tree.yview)
        self.accounts_tree.configure(yscrollcommand=scrollbar.set)

        self.accounts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Кнопки управления счетами
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="➕ Добавить счёт",
                   command=self.add_account_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❌ Удалить счёт",
                   command=self.delete_account).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 Обновить",
                   command=self.refresh_accounts_list).pack(side=tk.LEFT, padx=5)

    def add_account_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Новый счёт")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Название счёта:", font=("Helvetica", 12)).pack(pady=10)
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.pack(pady=5)

        ttk.Label(dialog, text="Начальный баланс:", font=("Helvetica", 12)).pack(pady=10)
        balance_entry = ttk.Entry(dialog, width=30)
        balance_entry.insert(0, "0.0")
        balance_entry.pack(pady=5)

        def create_account():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Введите название счёта")
                return
            if any(acc.name == name for acc in self.bank.accounts):
                messagebox.showerror("Ошибка", f"Счёт с именем '{name}' уже существует")
                return
            try:
                balance = float(balance_entry.get())
            except ValueError:
                messagebox.showerror("Ошибка", "Неверное число")
                return

            self.bank.add_account(name, balance)
            save_data(self.bank)
            self.refresh_accounts_list()
            self.update_account_combos()
            messagebox.showinfo("Успех", f"Счёт '{name}' создан")
            dialog.destroy()

        ttk.Button(dialog, text="Создать", command=create_account).pack(pady=20)

    def delete_account(self):
        selected = self.accounts_tree.selection()
        if not selected:
            messagebox.showwarning("Удаление", "Выберите счёт для удаления")
            return
        item = self.accounts_tree.item(selected[0])
        account_name = item['values'][0]

        if messagebox.askyesno("Подтверждение", f"Удалить счёт '{account_name}'? Все транзакции будут потеряны."):
            self.bank.remove_account(account_name)
            save_data(self.bank)
            self.refresh_accounts_list()
            self.update_account_combos()
            self.refresh_trans_list()
            self.refresh_limits_list()
            self.status_bar.config(text=f"Счёт '{account_name}' удалён")

    def refresh_accounts_list(self):
        for row in self.accounts_tree.get_children():
            self.accounts_tree.delete(row)
        for acc in self.bank.accounts:
            self.accounts_tree.insert("", tk.END, values=(
                acc.name,
                f"{acc.balance:,.2f} ₽"
            ))
        total = self.bank.total_balance()
        self.total_balance_label.config(text=f"💰 {total:,.2f} ₽")

    # ------------------------------------------------------------------
    # Вкладка "Транзакции"
    # ------------------------------------------------------------------
    def setup_trans_tab(self):
        frame = self.tab_trans

        # Создаем две колонки
        left_frame = ttk.Frame(frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        right_frame = ttk.Frame(frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        # Левая колонка - форма добавления
        add_frame = ttk.LabelFrame(left_frame, text="➕ Добавить транзакцию", padding=15)
        add_frame.pack(fill=tk.BOTH, expand=True)

        # Выбор счёта
        ttk.Label(add_frame, text="Счёт:", font=("Helvetica", 11)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.trans_account = ttk.Combobox(add_frame, values=[], width=20, state="readonly")
        self.trans_account.grid(row=0, column=1, pady=5, padx=5)
        if self.bank.accounts:
            self.trans_account.set(self.bank.accounts[0].name)

        # Сумма
        ttk.Label(add_frame, text="Сумма (₽):", font=("Helvetica", 11)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.trans_amount = ttk.Entry(add_frame, width=20)
        self.trans_amount.grid(row=1, column=1, pady=5, padx=5)

        # Тип
        ttk.Label(add_frame, text="Тип:", font=("Helvetica", 11)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.trans_type = ttk.Combobox(add_frame, values=["Доход", "Расход"], width=20, state="readonly")
        self.trans_type.grid(row=2, column=1, pady=5, padx=5)
        self.trans_type.set("Расход")

        # Категория
        ttk.Label(add_frame, text="Категория:", font=("Helvetica", 11)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.trans_category = ttk.Entry(add_frame, width=20)
        self.trans_category.grid(row=3, column=1, pady=5, padx=5)

        # Описание
        ttk.Label(add_frame, text="Описание:", font=("Helvetica", 11)).grid(row=4, column=0, sticky=tk.W, pady=5)
        self.trans_desc = ttk.Entry(add_frame, width=20)
        self.trans_desc.grid(row=4, column=1, pady=5, padx=5)

        # Дата
        ttk.Label(add_frame, text="Дата (ГГГГ-ММ-ДД):", font=("Helvetica", 11)).grid(row=5, column=0, sticky=tk.W, pady=5)
        self.trans_date = ttk.Entry(add_frame, width=20)
        self.trans_date.grid(row=5, column=1, pady=5, padx=5)
        self.trans_date.insert(0, date.today().strftime("%Y-%m-%d"))

        ttk.Button(add_frame, text="💾 Добавить",
                   command=self.add_transaction_gui,
                   width=20).grid(row=6, column=0, columnspan=2, pady=20)

        # Правая колонка - фильтры, список и кнопка удаления
        filter_frame = ttk.LabelFrame(right_frame, text="🔍 Фильтры", padding=15)
        filter_frame.pack(fill=tk.X, pady=5)

        # Счёт
        ttk.Label(filter_frame, text="Счёт:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.filter_account = ttk.Combobox(filter_frame, values=["Все"], width=15, state="readonly")
        self.filter_account.grid(row=0, column=1, padx=5)
        self.filter_account.set("Все")

        # Даты
        ttk.Label(filter_frame, text="Начало:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.filter_start = ttk.Entry(filter_frame, width=12)
        self.filter_start.grid(row=1, column=1, padx=5)

        ttk.Label(filter_frame, text="Конец:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.filter_end = ttk.Entry(filter_frame, width=12)
        self.filter_end.grid(row=2, column=1, padx=5)

        # Категория
        ttk.Label(filter_frame, text="Категория:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.filter_category = ttk.Entry(filter_frame, width=15)
        self.filter_category.grid(row=3, column=1, padx=5)

        ttk.Button(filter_frame, text="Применить",
                   command=self.refresh_trans_list).grid(row=4, column=0, columnspan=2, pady=10)

        # Таблица транзакций
        trans_list_frame = ttk.LabelFrame(right_frame, text="📋 Список транзакций", padding=15)
        trans_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        columns = ("account", "date", "type", "amount", "category", "description")
        self.trans_tree = ttk.Treeview(
            trans_list_frame,
            columns=columns,
            show="headings",
            height=12
        )
        self.trans_tree.heading("account", text="Счёт")
        self.trans_tree.heading("date", text="Дата")
        self.trans_tree.heading("type", text="Тип")
        self.trans_tree.heading("amount", text="Сумма")
        self.trans_tree.heading("category", text="Категория")
        self.trans_tree.heading("description", text="Описание")

        self.trans_tree.column("account", width=80)
        self.trans_tree.column("date", width=80)
        self.trans_tree.column("type", width=60)
        self.trans_tree.column("amount", width=80)
        self.trans_tree.column("category", width=100)
        self.trans_tree.column("description", width=150)

        scrollbar = ttk.Scrollbar(trans_list_frame, orient=tk.VERTICAL, command=self.trans_tree.yview)
        self.trans_tree.configure(yscrollcommand=scrollbar.set)

        self.trans_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Кнопка удаления транзакции
        ttk.Button(right_frame, text="❌ Удалить выбранную транзакцию",
                   command=self.delete_transaction).pack(pady=5)

    def update_account_combos(self):
        """Обновить выпадающие списки счетов"""
        account_names = [acc.name for acc in self.bank.accounts]
        if hasattr(self, 'trans_account'):
            self.trans_account['values'] = account_names
            if account_names:
                self.trans_account.set(account_names[0])
        if hasattr(self, 'filter_account'):
            self.filter_account['values'] = ["Все"] + account_names
            self.filter_account.set("Все")

    def add_transaction_gui(self):
        try:
            account_name = self.trans_account.get()
            if not account_name:
                messagebox.showerror("Ошибка", "Выберите счёт")
                return

            amount = float(self.trans_amount.get())
            if amount <= 0:
                messagebox.showerror("Ошибка", "Сумма должна быть положительной")
                return

            trans_type = "income" if self.trans_type.get() == "Доход" else "expense"
            category = self.trans_category.get().strip()
            description = self.trans_desc.get().strip()
            date_str = self.trans_date.get().strip()

            if not category:
                messagebox.showerror("Ошибка", "Введите категорию")
                return

            t = Transaction(amount, category, description, trans_type, date_str)
            self.bank.add_transaction(account_name, t)
            save_data(self.bank)

            if hasattr(self.bank, 'limit_exceeded') and self.bank.limit_exceeded:
                cat, total, limit = self.bank.limit_exceeded
                messagebox.showwarning(
                    "Превышение лимита",
                    f"По категории '{cat}' превышен лимит!\n"
                    f"Траты в этом месяце: {total:.2f}, лимит: {limit:.2f}"
                )

            self.refresh_accounts_list()
            self.refresh_trans_list()
            self.refresh_limits_list()
            self.clear_add_transaction_fields()
            self.status_bar.config(text=f"✅ Транзакция добавлена: {amount} ₽")
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат суммы или даты")

    def clear_add_transaction_fields(self):
        self.trans_amount.delete(0, tk.END)
        self.trans_category.delete(0, tk.END)
        self.trans_desc.delete(0, tk.END)
        self.trans_date.delete(0, tk.END)
        self.trans_date.insert(0, date.today().strftime("%Y-%m-%d"))

    def delete_transaction(self):
        selected = self.trans_tree.selection()
        if not selected:
            messagebox.showwarning("Удаление", "Выберите транзакцию для удаления")
            return
        item = self.trans_tree.item(selected[0])
        values = item['values']
        # Получаем данные: account, date, type, amount, category, description
        account_name = values[0]
        date_str = values[1]
        trans_type = "income" if values[2] == "Доход" else "expense"
        amount_str = values[3].replace('+', '').replace('-', '').replace('₽', '').strip()
        amount = float(amount_str.replace(',', ''))
        category = values[4]
        description = values[5]

        # Найдем транзакцию в банке (по точному совпадению полей)
        acc = self.bank.get_account(account_name)
        transaction_to_delete = None
        for t in acc.transactions:
            if (t.date.strftime("%Y-%m-%d") == date_str and
                t.type == trans_type and
                abs(t.amount - amount) < 0.01 and
                t.category == category and
                t.description == description):
                transaction_to_delete = t
                break

        if transaction_to_delete and messagebox.askyesno("Подтверждение", "Удалить выбранную транзакцию?"):
            self.bank.remove_transaction(account_name, transaction_to_delete)
            save_data(self.bank)
            self.refresh_accounts_list()
            self.refresh_trans_list()
            self.refresh_limits_list()
            self.status_bar.config(text="Транзакция удалена")

    def refresh_trans_list(self):
        for row in self.trans_tree.get_children():
            self.trans_tree.delete(row)

        account_filter = self.filter_account.get()
        if account_filter == "Все":
            account_name = None
        else:
            account_name = account_filter

        start_str = self.filter_start.get().strip()
        end_str = self.filter_end.get().strip()
        cat = self.filter_category.get().strip() or None

        start_date = None
        end_date = None
        if start_str:
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Ошибка", "Неверный формат начальной даты")
                return
        if end_str:
            try:
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Ошибка", "Неверный формат конечной даты")
                return

        transactions = self.bank.get_all_transactions(start_date, end_date, cat, account_name)
        for acc_name, t in transactions:
            sign = "+" if t.type == "income" else "-"
            trans_type_ru = "Доход" if t.type == "income" else "Расход"
            self.trans_tree.insert("", tk.END, values=(
                acc_name,
                t.date.strftime("%Y-%m-%d"),
                trans_type_ru,
                f"{sign}{t.amount:.2f} ₽",
                t.category,
                t.description
            ))

    # ------------------------------------------------------------------
    # Вкладка "Отчёты"
    # ------------------------------------------------------------------
    def setup_reports_tab(self):
        frame = self.tab_reports

        # Верхняя панель с параметрами
        params_frame = ttk.LabelFrame(frame, text="📅 Параметры отчёта", padding=15)
        params_frame.pack(fill=tk.X, pady=10)

        # Счёт
        ttk.Label(params_frame, text="Счёт:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.report_account = ttk.Combobox(params_frame, values=["Все"], width=15, state="readonly")
        self.report_account.grid(row=0, column=1, padx=5)
        self.report_account.set("Все")

        # Период
        ttk.Label(params_frame, text="Начало:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.report_start = ttk.Entry(params_frame, width=12)
        self.report_start.grid(row=1, column=1, padx=5)
        self.report_start.insert(0, date.today().replace(day=1).strftime("%Y-%m-%d"))

        ttk.Label(params_frame, text="Конец:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.report_end = ttk.Entry(params_frame, width=12)
        self.report_end.grid(row=2, column=1, padx=5)
        self.report_end.insert(0, date.today().strftime("%Y-%m-%d"))

        # Кнопки
        btn_frame = ttk.Frame(params_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="📊 Сформировать",
                   command=self.generate_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🥧 Диаграмма",
                   command=self.show_pie_chart).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="💾 Экспорт",
                   command=self.export_report).pack(side=tk.LEFT, padx=2)

        # Текстовое поле для отчёта
        report_frame = ttk.LabelFrame(frame, text="📄 Результат", padding=15)
        report_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.report_text = tk.Text(
            report_frame,
            wrap=tk.WORD,
            font=("Courier", 10),
            height=20
        )
        self.report_text.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(report_frame, orient=tk.VERTICAL, command=self.report_text.yview)
        self.report_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def get_report_period(self):
        start_str = self.report_start.get().strip()
        end_str = self.report_end.get().strip()
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат даты")
            return None, None, None

        if start_date > end_date:
            messagebox.showerror("Ошибка", "Начальная дата позже конечной")
            return None, None, None

        account_name = self.report_account.get()
        if account_name == "Все":
            account_name = None
        return start_date, end_date, account_name

    def generate_report(self):
        start_date, end_date, account_name = self.get_report_period()
        if start_date is None:
            return

        income, expense, by_cat = self.bank.report_period(start_date, end_date, account_name)

        lines = []
        if account_name:
            lines.append(f"📊 Отчёт по счёту '{account_name}'")
        else:
            lines.append("📊 Отчёт по всем счетам")
        lines.append(f"Период: {start_date} — {end_date}")
        lines.append("=" * 60)
        lines.append(f"💰 Доходы:  {income:>12,.2f} ₽")
        lines.append(f"💸 Расходы: {expense:>12,.2f} ₽")
        if income > 0:
            savings_rate = (income - expense) / income * 100
            lines.append(f"💎 Сбережения: {income - expense:>12,.2f} ₽ ({savings_rate:.1f}%)")
        lines.append("-" * 60)
        lines.append("📈 Расходы по категориям:")
        if by_cat:
            for cat, amt in sorted(by_cat.items(), key=lambda x: x[1], reverse=True):
                percent = (amt / expense * 100) if expense > 0 else 0
                lines.append(f"  {cat:25} {amt:>12,.2f} ₽ ({percent:.1f}%)")
        else:
            lines.append("  Нет расходов")

        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(1.0, "\n".join(lines))
        self.status_bar.config(text="✅ Отчёт сформирован")

    def show_pie_chart(self):
        start_date, end_date, account_name = self.get_report_period()
        if start_date is None:
            return

        _, _, by_cat = self.bank.report_period(start_date, end_date, account_name)
        if not by_cat:
            messagebox.showinfo("Диаграмма", "Нет расходов за выбранный период")
            return

        chart_win = tk.Toplevel(self.root)
        chart_win.title("🥧 Круговая диаграмма расходов")
        chart_win.geometry("700x600")
        chart_win.transient(self.root)

        canvas_frame = ttk.Frame(chart_win)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(canvas_frame, width=400, height=400, bg='white')
        canvas.pack()

        legend_frame = ttk.LabelFrame(chart_win, text="Легенда", padding=10)
        legend_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        center_x, center_y = 200, 200
        radius = 150

        total = sum(by_cat.values())
        start_angle = 0
        colors = {}

        for cat, amount in by_cat.items():
            if cat not in colors:
                colors[cat] = random_color()
            extent = (amount / total) * 360
            canvas.create_arc(
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius,
                start=start_angle, extent=extent,
                fill=colors[cat], outline='black', width=2
            )
            start_angle += extent

        for cat, amount in sorted(by_cat.items(), key=lambda x: x[1], reverse=True):
            color = colors[cat]
            item_frame = ttk.Frame(legend_frame)
            item_frame.pack(anchor=tk.W, pady=2)

            color_box = tk.Canvas(item_frame, width=20, height=20, bg=color,
                                  highlightthickness=1, highlightbackground='black')
            color_box.pack(side=tk.LEFT, padx=5)

            percent = (amount / total) * 100
            ttk.Label(
                item_frame,
                text=f"{cat}: {amount:,.2f} ₽ ({percent:.1f}%)",
                font=("Helvetica", 10)
            ).pack(side=tk.LEFT)

    def export_report(self):
        start_date, end_date, account_name = self.get_report_period()
        if start_date is None:
            return

        income, expense, by_cat = self.bank.report_period(start_date, end_date, account_name)

        lines = []
        if account_name:
            lines.append(f"Отчёт по счёту '{account_name}'")
        else:
            lines.append("Отчёт по всем счетам")
        lines.append(f"Период: {start_date} — {end_date}")
        lines.append("=" * 60)
        lines.append(f"Доходы:  {income:>12,.2f} ₽")
        lines.append(f"Расходы: {expense:>12,.2f} ₽")
        if income > 0:
            savings_rate = (income - expense) / income * 100
            lines.append(f"Сбережения: {income - expense:>12,.2f} ₽ ({savings_rate:.1f}%)")
        lines.append("-" * 60)
        lines.append("Расходы по категориям:")
        if by_cat:
            for cat, amt in sorted(by_cat.items()):
                lines.append(f"  {cat:25} {amt:>12,.2f} ₽")
        else:
            lines.append("  Нет расходов")

        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            messagebox.showinfo("Экспорт", f"✅ Отчёт сохранён в файл {filename}")
            self.status_bar.config(text=f"✅ Отчёт экспортирован в {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"❌ Не удалось сохранить файл: {e}")

    # ------------------------------------------------------------------
    # Вкладка "Лимиты"
    # ------------------------------------------------------------------
    def setup_limits_tab(self):
        frame = self.tab_limits

        # Панель добавления лимита
        add_frame = ttk.LabelFrame(frame, text="⚡ Установить лимит", padding=15)
        add_frame.pack(fill=tk.X, pady=10)

        ttk.Label(add_frame, text="Категория:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.limit_category = ttk.Entry(add_frame, width=20)
        self.limit_category.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(add_frame, text="Лимит (₽/мес):").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.limit_amount = ttk.Entry(add_frame, width=20)
        self.limit_amount.grid(row=1, column=1, padx=5, pady=5)

        btn_frame = ttk.Frame(add_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="💾 Установить",
                   command=self.set_limit_gui).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🔍 Проверить все",
                   command=self.check_limits_gui).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="❌ Удалить лимит",
                   command=self.delete_limit).pack(side=tk.LEFT, padx=2)

        # Список текущих лимитов
        list_frame = ttk.LabelFrame(frame, text="📋 Текущие лимиты", padding=15)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        columns = ("category", "limit", "status")
        self.limits_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=10
        )
        self.limits_tree.heading("category", text="Категория")
        self.limits_tree.heading("limit", text="Лимит (₽/мес)")
        self.limits_tree.heading("status", text="Статус")

        self.limits_tree.column("category", width=200)
        self.limits_tree.column("limit", width=150)
        self.limits_tree.column("status", width=150)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.limits_tree.yview)
        self.limits_tree.configure(yscrollcommand=scrollbar.set)

        self.limits_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def set_limit_gui(self):
        category = self.limit_category.get().strip()
        if not category:
            messagebox.showerror("Ошибка", "Введите категорию")
            return
        try:
            amount = float(self.limit_amount.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректную сумму")
            return

        self.bank.set_limit(category, amount)
        save_data(self.bank)
        self.refresh_limits_list()
        self.limit_category.delete(0, tk.END)
        self.limit_amount.delete(0, tk.END)
        messagebox.showinfo("Успех", f"✅ Лимит для '{category}' установлен")
        self.status_bar.config(text=f"✅ Лимит для '{category}' установлен")

    def delete_limit(self):
        selected = self.limits_tree.selection()
        if not selected:
            messagebox.showwarning("Удаление", "Выберите лимит для удаления")
            return
        item = self.limits_tree.item(selected[0])
        category = item['values'][0]

        if messagebox.askyesno("Подтверждение", f"Удалить лимит для категории '{category}'?"):
            self.bank.remove_limit(category)
            save_data(self.bank)
            self.refresh_limits_list()
            self.status_bar.config(text=f"Лимит для '{category}' удалён")

    def refresh_limits_list(self):
        for row in self.limits_tree.get_children():
            self.limits_tree.delete(row)

        today = date.today()
        for cat, lim in self.bank.limits.items():
            spent = 0.0
            for acc in self.bank.accounts:
                for t in acc.transactions:
                    if (t.type == "expense" and t.category == cat and
                            t.date.month == today.month and t.date.year == today.year):
                        spent += t.amount

            status = "✅ В норме" if spent <= lim else f"⚠️ Превышен ({spent:.2f} / {lim:.2f})"

            self.limits_tree.insert("", tk.END, values=(
                cat,
                f"{lim:,.2f} ₽",
                status
            ))

    def check_limits_gui(self):
        warnings = self.bank.check_limits()
        if warnings:
            msg = "❌ Превышение лимитов:\n\n" + "\n".join(warnings)
            messagebox.showwarning("Проверка лимитов", msg)
        else:
            messagebox.showinfo("Проверка лимитов", "✅ Все лимиты соблюдены")
        self.refresh_limits_list()


# ----------------------------------------------------------------------
# Запуск приложения
# ----------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = BankApp(root)
    root.mainloop()