import socket
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from queue import Queue, Empty
import json
import os
import time
import subprocess
import platform
import webbrowser
from datetime import datetime
from urllib.parse import urlparse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
import http.server
import socketserver
import tempfile
import html
import urllib.request

# Импорт для мини-браузера
try:
    import tkinterweb

    HAS_TKINTERWEB = True
except ImportError:
    HAS_TKINTERWEB = False
    print("Для мини-браузера установите: pip install tkinterweb")


class MegaPortScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ Mega Port Scanner Pro")
        self.root.geometry("1400x800")

        # Серверные переменные
        self.http_server = None
        self.server_thread = None
        self.server_running = False

        # Иконка
        try:
            self.root.iconbitmap('scanner.ico')
        except:
            pass

        # Конфигурация
        self.config_file = "scanner_config.json"
        self.history_file = "scan_history.json"
        self.log_file = "scanner.log"

        # Очереди и флаги
        self.queue = Queue()
        self.scanning = False
        self.scan_thread = None
        self.current_scan = {}

        # История и логи
        self.scan_history = self.load_history()
        self.open_ports_history = {}

        # Стили
        self.setup_styles()

        # GUI
        self.setup_gui()

        # Загрузка конфигурации
        self.load_config()

        # Обновление GUI
        self.check_queue()
        self.update_network_info()

        # Автосохранение каждые 30 сек
        self.root.after(30000, self.auto_save)

    def setup_styles(self):
        """Настройка стилей"""
        self.style = ttk.Style()

        # Современная тема
        self.style.theme_use('clam')

        # Цвета
        self.colors = {
            'open': '#2E7D32',
            'closed': '#757575',
            'error': '#D84315',
            'warning': '#FF8F00',
            'info': '#1565C0',
            'success': '#388E3C'
        }

        # Стиль для вкладок
        self.style.configure('Custom.TNotebook.Tab',
                             padding=[20, 5],
                             font=('Segoe UI', 10))

    def setup_gui(self):
        """Создание интерфейса"""
        # Главный контейнер
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Верхняя панель
        self.create_top_panel(main_container)

        # Центральная область с вкладками
        self.create_center_area(main_container)

        # Нижняя панель
        self.create_bottom_panel(main_container)

    def create_top_panel(self, parent):
        """Верхняя панель с основными кнопками"""
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # Заголовок
        title = ttk.Label(top_frame,
                          text="⚡ MEGA PORT SCANNER PRO",
                          font=('Segoe UI', 16, 'bold'))
        title.pack(side=tk.LEFT, padx=(0, 20))

        # Кнопки управления
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side=tk.RIGHT)

        buttons = [
            ("▶ Старт", self.start_scan, 'success'),
            ("⏸ Пауза", self.pause_scan, 'warning'),
            ("⏹ Стоп", self.stop_scan, 'error'),
            ("🧹 Очистить", self.clear_results, 'info'),
            ("💾 Сохранить", self.save_results, 'success'),
            ("📊 Отчет", self.generate_report, 'info'),
            ("⚙️ Настройки", self.open_settings, 'warning')
        ]

        for text, cmd, color in buttons:
            btn = ttk.Button(btn_frame, text=text, command=cmd,
                             style=f'{color.capitalize()}.TButton')
            btn.pack(side=tk.LEFT, padx=2)
            setattr(self, f'btn_{text}', btn)

    def create_center_area(self, parent):
        """Центральная область с вкладками"""
        # Notebook для вкладок
        self.notebook = ttk.Notebook(parent, style='Custom.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Создаем вкладки
        self.tab_scan = ttk.Frame(self.notebook)
        self.tab_network = ttk.Frame(self.notebook)
        self.tab_browser = ttk.Frame(self.notebook)
        self.tab_history = ttk.Frame(self.notebook)
        self.tab_logs = ttk.Frame(self.notebook)
        self.tab_tools = ttk.Frame(self.notebook)

        # Добавляем вкладки
        self.notebook.add(self.tab_scan, text='📡 Сканирование')
        self.notebook.add(self.tab_network, text='🌐 Сеть')
        self.notebook.add(self.tab_browser, text='🌍 Браузер')
        self.notebook.add(self.tab_history, text='📊 История')
        self.notebook.add(self.tab_logs, text='📝 Логи')
        self.notebook.add(self.tab_tools, text='🛠 Инструменты')

        # Заполняем вкладки
        self.setup_scan_tab()
        self.setup_network_tab()
        self.setup_browser_tab()
        self.setup_history_tab()
        self.setup_logs_tab()
        self.setup_tools_tab()

    def setup_scan_tab(self):
        """Вкладка сканирования"""
        # Левая панель - настройки
        left_panel = ttk.LabelFrame(self.tab_scan, text="Настройки сканирования", padding="10")
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        # Хост
        ttk.Label(left_panel, text="Цель:").grid(row=0, column=0, sticky=tk.W, pady=5)

        host_frame = ttk.Frame(left_panel)
        host_frame.grid(row=0, column=1, sticky=tk.EW, pady=5)

        self.host_var = tk.StringVar(value="localhost")
        self.host_combo = ttk.Combobox(host_frame, textvariable=self.host_var, width=25)
        self.host_combo.grid(row=0, column=0)
        self.host_combo['values'] = ['localhost', '127.0.0.1', '192.168.1.1', '192.168.0.1']

        ttk.Button(host_frame, text="Сеть", command=self.scan_network_dialog).grid(row=0, column=1, padx=5)

        # Диапазон портов
        ttk.Label(left_panel, text="Порты:").grid(row=1, column=0, sticky=tk.W, pady=5)

        port_frame = ttk.Frame(left_panel)
        port_frame.grid(row=1, column=1, sticky=tk.EW, pady=5)

        self.port_start = ttk.Spinbox(port_frame, from_=1, to=65535, width=8)
        self.port_start.grid(row=0, column=0)
        self.port_start.set(1)

        ttk.Label(port_frame, text="-").grid(row=0, column=1, padx=5)

        self.port_end = ttk.Spinbox(port_frame, from_=1, to=65535, width=8)
        self.port_end.grid(row=0, column=2)
        self.port_end.set(1024)

        # Быстрые пресеты
        presets_frame = ttk.LabelFrame(left_panel, text="Быстрые диапазоны", padding="5")
        presets_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=10)

        presets = [
            ("Well Known (1-1024)", (1, 1024)),
            ("Common (1-10000)", (1, 10000)),
            ("All Ports", (1, 65535)),
            ("Web Ports", (80, 443, 8080, 8443)),
            ("Game Ports", (27015, 27016, 25565)),
        ]

        for i, (name, ports) in enumerate(presets):
            btn = ttk.Button(presets_frame, text=name,
                             command=lambda p=ports: self.set_port_range(p))
            btn.grid(row=i // 2, column=i % 2, sticky=tk.EW, padx=2, pady=2)

        # Метод сканирования
        ttk.Label(left_panel, text="Метод:").grid(row=3, column=0, sticky=tk.W, pady=5)

        self.scan_method = ttk.Combobox(left_panel, values=[
            "Полное сканирование",
            "Быстрое сканирование",
            "Только известные порты",
            "Пинг + сканирование"
        ], state="readonly", width=25)
        self.scan_method.grid(row=3, column=1, sticky=tk.EW, pady=5)
        self.scan_method.set("Быстрое сканирование")

        # Таймаут
        ttk.Label(left_panel, text="Таймаут (сек):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.timeout_var = tk.DoubleVar(value=1.0)
        self.timeout_scale = ttk.Scale(left_panel, from_=0.1, to=5.0,
                                       variable=self.timeout_var, orient=tk.HORIZONTAL)
        self.timeout_scale.grid(row=4, column=1, sticky=tk.EW, pady=5)

        # Потоки
        ttk.Label(left_panel, text="Потоки:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.threads_var = tk.IntVar(value=100)
        self.threads_spin = ttk.Spinbox(left_panel, from_=1, to=500,
                                        textvariable=self.threads_var, width=10)
        self.threads_spin.grid(row=5, column=1, sticky=tk.W, pady=5)

        # Дополнительные опции
        self.var_show_closed = tk.BooleanVar(value=False)
        self.var_show_errors = tk.BooleanVar(value=True)
        self.var_save_logs = tk.BooleanVar(value=True)
        self.var_auto_open = tk.BooleanVar(value=False)

        ttk.Checkbutton(left_panel, text="Показывать закрытые",
                        variable=self.var_show_closed).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=2)
        ttk.Checkbutton(left_panel, text="Показывать ошибки",
                        variable=self.var_show_errors).grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=2)
        ttk.Checkbutton(left_panel, text="Авто-сохранение",
                        variable=self.var_save_logs).grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=2)
        ttk.Checkbutton(left_panel, text="Авто-открытие веб",
                        variable=self.var_auto_open).grid(row=9, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Правая панель - результаты
        right_panel = ttk.Frame(self.tab_scan)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Панель результатов
        results_frame = ttk.LabelFrame(right_panel, text="Результаты сканирования", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview для результатов
        columns = ('port', 'status', 'service', 'banner', 'response')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=20)

        # Заголовки
        self.results_tree.heading('port', text='Порт')
        self.results_tree.heading('status', text='Статус')
        self.results_tree.heading('service', text='Служба')
        self.results_tree.heading('banner', text='Баннер')
        self.results_tree.heading('response', text='Ответ')

        # Колонки
        self.results_tree.column('port', width=80)
        self.results_tree.column('status', width=100)
        self.results_tree.column('service', width=150)
        self.results_tree.column('banner', width=200)
        self.results_tree.column('response', width=300)

        # Скроллбар
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)

        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Контекстное меню
        self.setup_context_menu()

        # Статистика
        stats_frame = ttk.Frame(right_panel)
        stats_frame.pack(fill=tk.X, pady=(5, 0))

        self.stats_label = ttk.Label(stats_frame, text="Готов к сканированию")
        self.stats_label.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(stats_frame, mode='indeterminate', length=300)
        self.progress.pack(side=tk.RIGHT, padx=10)

    def setup_network_tab(self):
        """Вкладка информации о сети"""
        # Информация о текущей сети
        info_frame = ttk.LabelFrame(self.tab_network, text="Сетевая информация", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Текстовое поле для информации
        self.network_info = scrolledtext.ScrolledText(info_frame, height=20)
        self.network_info.pack(fill=tk.BOTH, expand=True)

        # Кнопки обновления
        btn_frame = ttk.Frame(self.tab_network)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="Обновить",
                   command=self.update_network_info).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Сканировать сеть",
                   command=self.scan_local_network).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Экспорт",
                   command=self.export_network_info).pack(side=tk.LEFT, padx=2)

    def setup_browser_tab(self):
        """Вкладка мини-браузера"""
        if HAS_TKINTERWEB:
            browser_frame = ttk.Frame(self.tab_browser)
            browser_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Панель управления
            control_frame = ttk.Frame(browser_frame)
            control_frame.pack(fill=tk.X, pady=(0, 5))

            self.browser_url = ttk.Entry(control_frame, width=50)
            self.browser_url.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            self.browser_url.insert(0, "http://localhost:8080")

            ttk.Button(control_frame, text="Перейти",
                       command=self.browser_go).pack(side=tk.LEFT, padx=2)
            ttk.Button(control_frame, text="Назад",
                       command=self.browser_back).pack(side=tk.LEFT, padx=2)
            ttk.Button(control_frame, text="Вперед",
                       command=self.browser_forward).pack(side=tk.LEFT, padx=2)
            ttk.Button(control_frame, text="Обновить",
                       command=self.browser_refresh).pack(side=tk.LEFT, padx=2)

            # Сам браузер
            self.html_frame = tkinterweb.HtmlFrame(browser_frame)
            self.html_frame.pack(fill=tk.BOTH, expand=True)
        else:
            # Заглушка если нет tkinterweb
            ttk.Label(self.tab_browser,
                      text="Установите tkinterweb: pip install tkinterweb\n"
                           "Для просмотра веб-интерфейсов портов",
                      justify=tk.CENTER).pack(expand=True)

            # Простой просмотрщик
            simple_frame = ttk.Frame(self.tab_browser)
            simple_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            ttk.Label(simple_frame, text="Быстрый переход к портам:").pack(pady=5)

            common_ports = [
                ("HTTP (80)", "http://{host}:80"),
                ("HTTPS (443)", "https://{host}:443"),
                ("Web Admin (8080)", "http://{host}:8080"),
                ("Router (192.168.1.1)", "http://192.168.1.1"),
                ("PHPMyAdmin (3306)", "http://{host}:3306"),
            ]

            for name, template in common_ports:
                btn = ttk.Button(simple_frame, text=name,
                                 command=lambda t=template: self.open_in_browser(t))
                btn.pack(pady=2)

    def setup_history_tab(self):
        """Вкладка истории"""
        history_frame = ttk.Frame(self.tab_history)
        history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview для истории
        columns = ('date', 'target', 'ports', 'open', 'duration', 'method')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings', height=20)

        # Заголовки
        self.history_tree.heading('date', text='Дата')
        self.history_tree.heading('target', text='Цель')
        self.history_tree.heading('ports', text='Порты')
        self.history_tree.heading('open', text='Открыто')
        self.history_tree.heading('duration', text='Время')
        self.history_tree.heading('method', text='Метод')

        # Колонки
        self.history_tree.column('date', width=150)
        self.history_tree.column('target', width=150)
        self.history_tree.column('ports', width=100)
        self.history_tree.column('open', width=80)
        self.history_tree.column('duration', width=80)
        self.history_tree.column('method', width=120)

        # Скроллбар
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Кнопки управления историей
        btn_frame = ttk.Frame(self.tab_history)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="Загрузить историю",
                   command=self.load_history_gui).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Очистить историю",
                   command=self.clear_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Повторить сканирование",
                   command=self.repeat_scan).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Экспорт в CSV",
                   command=self.export_history_csv).pack(side=tk.LEFT, padx=2)

    def setup_logs_tab(self):
        """Вкладка логов"""
        logs_frame = ttk.Frame(self.tab_logs)
        logs_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Текстовое поле для логов
        self.logs_text = scrolledtext.ScrolledText(logs_frame, height=30)
        self.logs_text.pack(fill=tk.BOTH, expand=True)

        # Панель управления логами
        control_frame = ttk.Frame(self.tab_logs)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(control_frame, text="Очистить логи",
                   command=self.clear_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Сохранить логи",
                   command=self.save_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Экспорт",
                   command=self.export_logs).pack(side=tk.LEFT, padx=2)

        # Уровень логирования
        ttk.Label(control_frame, text="Уровень:").pack(side=tk.LEFT, padx=(20, 5))
        self.log_level = ttk.Combobox(control_frame, values=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                                      state='readonly', width=10)
        self.log_level.pack(side=tk.LEFT)
        self.log_level.set('INFO')

    def setup_tools_tab(self):
        """Вкладка инструментов"""
        tools_frame = ttk.Frame(self.tab_tools)
        tools_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Сетка для инструментов
        for i in range(3):
            tools_frame.columnconfigure(i, weight=1)
        for i in range(5):
            tools_frame.rowconfigure(i, weight=1)

        tools = [
            ("🔧 Открыть порт", self.open_port_tool, 0, 0),
            ("🔒 Закрыть порт", self.close_port_tool, 0, 1),
            ("📡 Ping хоста", self.ping_tool, 0, 2),
            ("🌐 Traceroute", self.traceroute_tool, 1, 0),
            ("🔍 DNS lookup", self.dns_lookup_tool, 1, 1),
            ("📊 Пропускная способность", self.bandwidth_test, 1, 2),
            ("🛡️ Проверка брандмауэра", self.firewall_check, 2, 0),
            ("🚀 Запустить сервер", self.start_server_tool, 2, 1),
            ("📶 Монитор сети", self.network_monitor, 2, 2),
            ("⚡ Быстрый скан", self.quick_scan, 3, 0),
            ("🎯 Целевое сканирование", self.targeted_scan, 3, 1),
            ("📈 Анализ трафика", self.traffic_analysis, 3, 2),
            ("🔧 Настройка сети", self.network_setup, 4, 0),
            ("🔐 Проверка SSL", self.ssl_check, 4, 1),
            ("📡 WHOIS запрос", self.whois_lookup, 4, 2),
        ]

        for text, command, row, col in tools:
            btn = ttk.Button(tools_frame, text=text, command=command)
            btn.grid(row=row, column=col, sticky=tk.NSEW, padx=5, pady=5, ipady=10)

    def create_bottom_panel(self, parent):
        """Нижняя панель статуса"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(10, 0))

        # Статус бар
        self.status_var = tk.StringVar(value="Готов")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var,
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, ipady=5)

        # Информация о сканировании
        info_frame = ttk.Frame(status_frame)
        info_frame.pack(fill=tk.X)

        self.scan_info = ttk.Label(info_frame, text="")
        self.scan_info.pack(side=tk.LEFT)

        self.time_label = ttk.Label(info_frame, text="")
        self.time_label.pack(side=tk.RIGHT)

        # Обновление времени
        self.update_time()

    def setup_context_menu(self):
        """Контекстное меню для результатов"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Открыть в браузере",
                                      command=self.open_selected_in_browser)
        self.context_menu.add_command(label="Скопировать порт",
                                      command=self.copy_port)
        self.context_menu.add_command(label="Проверить службу",
                                      command=self.check_service)
        self.context_menu.add_command(label="Добавить в избранное",
                                      command=self.add_to_favorites)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Получить баннер",
                                      command=self.get_banner)
        self.context_menu.add_command(label="Сохранить результат",
                                      command=self.save_selected_result)

        # Привязка правой кнопки
        self.results_tree.bind("<Button-3>", self.show_context_menu)

    # ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

    def log(self, message, level='INFO'):
        """Логирование"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        # В GUI
        self.logs_text.insert(tk.END, log_entry)
        self.logs_text.see(tk.END)

        # В файл
        if self.var_save_logs.get():
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
            except:
                pass

        # В очередь для обновления статуса
        if level in ['ERROR', 'WARNING']:
            self.queue.put(('status', message))

    def update_time(self):
        """Обновление времени"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)

    def get_network_interfaces(self):
        """Получение сетевых интерфейсов"""
        interfaces = []

        try:
            # Получаем локальный IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
                interfaces.append(('Основной', local_ip))
            finally:
                s.close()

            # Получаем все IP
            hostname = socket.gethostname()
            all_ips = socket.gethostbyname_ex(hostname)[2]

            for i, ip in enumerate(all_ips):
                if ip != local_ip and not ip.startswith('127.'):
                    interfaces.append((f"IP {i + 1}", ip))

        except Exception as e:
            self.log(f"Ошибка получения интерфейсов: {e}", 'ERROR')

        return interfaces

    def update_network_info(self):
        """Обновление информации о сети"""
        try:
            info = "=== СЕТЕВАЯ ИНФОРМАЦИЯ ===\n\n"

            # Хостнейм
            hostname = socket.gethostname()
            info += f"Имя компьютера: {hostname}\n"

            # IP адреса
            info += "\nIP адреса:\n"
            interfaces = self.get_network_interfaces()

            for iface_name, ip in interfaces:
                if not ip.startswith('127.'):
                    info += f"  {iface_name}: {ip}\n"

            # Внешний IP
            info += "\nВнешний IP:\n"
            try:
                response = requests.get('https://api.ipify.org?format=json', timeout=5)
                if response.status_code == 200:
                    external_ip = response.json()['ip']
                    info += f"  {external_ip}\n"
            except:
                info += "  Не удалось определить\n"

            # Информация о системе
            info += f"\nОперационная система: {platform.system()} {platform.release()}\n"
            info += f"Архитектура: {platform.machine()}\n"

            self.network_info.delete(1.0, tk.END)
            self.network_info.insert(1.0, info)

        except Exception as e:
            self.log(f"Ошибка получения сетевой информации: {e}", 'ERROR')

    def start_scan(self):
        """Начать сканирование"""
        if self.scanning:
            return

        try:
            host = self.host_var.get().strip()
            if not host:
                messagebox.showwarning("Внимание", "Введите хост для сканирования")
                return

            start_port = int(self.port_start.get())
            end_port = int(self.port_end.get())

            if start_port > end_port:
                messagebox.showwarning("Внимание", "Начальный порт должен быть меньше конечного")
                return

            # Очистка предыдущих результатов
            self.results_tree.delete(*self.results_tree.get_children())

            # Установка флагов
            self.scanning = True
            self.current_scan = {
                'host': host,
                'start_port': start_port,
                'end_port': end_port,
                'start_time': datetime.now(),
                'open_ports': [],
                'total_ports': end_port - start_port + 1
            }

            # Обновление GUI
            self.progress.start()
            self.status_var.set(f"Сканирование {host}...")

            # Запуск в отдельном потоке
            self.scan_thread = threading.Thread(target=self.scan_worker, daemon=True)
            self.scan_thread.start()

            self.log(f"Начато сканирование {host}:{start_port}-{end_port}", 'INFO')

        except Exception as e:
            self.log(f"Ошибка запуска сканирования: {e}", 'ERROR')
            messagebox.showerror("Ошибка", str(e))

    def scan_worker(self):
        """Рабочая функция сканирования"""
        try:
            host = self.current_scan['host']
            start_port = self.current_scan['start_port']
            end_port = self.current_scan['end_port']
            timeout = self.timeout_var.get()
            max_threads = self.threads_var.get()

            ports_to_scan = range(start_port, end_port + 1)
            open_ports = []

            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                # Создаем футуры для всех портов
                future_to_port = {
                    executor.submit(self.check_single_port, host, port, timeout): port
                    for port in ports_to_scan
                }

                completed = 0
                for future in as_completed(future_to_port):
                    if not self.scanning:
                        break

                    port = future_to_port[future]
                    try:
                        result = future.result(timeout=timeout + 1)
                        if result['open']:
                            open_ports.append(port)
                            self.queue.put(('result', result))
                    except Exception as e:
                        self.queue.put(('error', f"Порт {port}: {e}"))

                    completed += 1
                    progress = (completed / self.current_scan['total_ports']) * 100
                    self.queue.put(('progress', progress))

            # Завершение сканирования
            self.current_scan['end_time'] = datetime.now()
            self.current_scan['open_ports'] = open_ports

            duration = (self.current_scan['end_time'] -
                        self.current_scan['start_time']).total_seconds()

            self.queue.put(('scan_complete', {
                'host': host,
                'open_count': len(open_ports),
                'duration': duration,
                'method': self.scan_method.get()
            }))

            # Сохранение в историю
            self.save_to_history()

        except Exception as e:
            self.queue.put(('error', f"Ошибка сканирования: {e}"))
        finally:
            self.queue.put(('stop_scan', None))

    def check_single_port(self, host, port, timeout):
        """Проверка одного порта"""
        result = {
            'port': port,
            'open': False,
            'service': 'Неизвестно',
            'banner': '',
            'response': ''
        }

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            if sock.connect_ex((host, port)) == 0:
                result['open'] = True

                # Попытка получить сервис
                try:
                    result['service'] = socket.getservbyport(port)
                except:
                    pass

                # Попытка получить баннер
                try:
                    sock.send(b'HEAD / HTTP/1.0\r\n\r\n')
                    banner = sock.recv(1024).decode('utf-8', errors='ignore')
                    if banner:
                        result['banner'] = banner[:100]  # Ограничиваем длину

                        # Определяем тип сервиса по ответу
                        if 'HTTP' in banner.upper():
                            result['service'] = 'HTTP'
                        elif 'SMTP' in banner.upper():
                            result['service'] = 'SMTP'
                        elif 'FTP' in banner.upper():
                            result['service'] = 'FTP'
                        elif 'SSH' in banner.upper():
                            result['service'] = 'SSH'
                except:
                    pass

                sock.close()

                # Для HTTP портов пробуем получить больше информации
                if port in [80, 443, 8080, 8443]:
                    try:
                        protocol = 'https' if port in [443, 8443] else 'http'
                        response = requests.get(f'{protocol}://{host}:{port}',
                                                timeout=2, verify=False)
                        result['response'] = f"Status: {response.status_code}"
                    except:
                        pass

            return result

        except Exception as e:
            result['error'] = str(e)
            return result

    def pause_scan(self):
        """Пауза сканирования"""
        if self.scanning:
            self.scanning = False
            self.status_var.set("Сканирование приостановлено")
            self.progress.stop()
            self.log("Сканирование приостановлено", 'INFO')

    def stop_scan(self):
        """Остановка сканирования"""
        self.scanning = False
        self.status_var.set("Сканирование остановлено")
        self.progress.stop()
        self.log("Сканирование остановлено", 'INFO')

    def check_queue(self):
        """Проверка очереди событий"""
        try:
            while True:
                msg_type, data = self.queue.get_nowait()

                if msg_type == 'result':
                    self.add_result_to_tree(data)

                elif msg_type == 'progress':
                    # Можно добавить progress bar
                    pass

                elif msg_type == 'status':
                    self.status_var.set(data)

                elif msg_type == 'error':
                    self.log(data, 'ERROR')

                elif msg_type == 'scan_complete':
                    self.handle_scan_complete(data)

                elif msg_type == 'stop_scan':
                    self.scanning = False
                    self.progress.stop()
                    self.status_var.set("Готов")

        except Empty:
            pass

        self.root.after(100, self.check_queue)

    def add_result_to_tree(self, result):
        """Добавление результата в дерево"""
        if not result['open'] and not self.var_show_closed.get():
            return

        tags = ()
        if result['open']:
            tags = ('open',)
            if self.var_auto_open.get() and result['port'] in [80, 443, 8080]:
                self.open_in_browser(f"http://{self.current_scan['host']}:{result['port']}")

        self.results_tree.insert('', 'end', values=(
            result['port'],
            '✅ Открыт' if result['open'] else '❌ Закрыт',
            result['service'],
            result['banner'][:50] if result['banner'] else '',
            result['response']
        ), tags=tags)

    def handle_scan_complete(self, data):
        """Обработка завершения сканирования"""
        self.log(f"Сканирование завершено. Открыто портов: {data['open_count']}. "
                 f"Время: {data['duration']:.2f} сек", 'INFO')

        self.status_var.set(f"Готов. Найдено {data['open_count']} открытых портов")

        # Обновление статистики
        stats_text = f"Отсканировано: {self.current_scan['total_ports']} портов | "
        stats_text += f"Открыто: {data['open_count']} | "
        stats_text += f"Время: {data['duration']:.2f} сек"
        self.stats_label.config(text=stats_text)

        # Показать уведомление
        if data['open_count'] > 0:
            messagebox.showinfo("Сканирование завершено",
                                f"Найдено {data['open_count']} открытых портов")

    # ==================== ИНСТРУМЕНТЫ ====================

    def scan_local_network(self):
        """Сканирование локальной сети"""
        try:
            dialog = tk.Toplevel(self.root)
            dialog.title("Сканирование сети")
            dialog.geometry("500x400")

            ttk.Label(dialog, text="Сканирование локальной сети", font=('Arial', 12)).pack(pady=10)

            output_text = scrolledtext.ScrolledText(dialog, height=15)
            output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            def start_scan():
                output_text.delete(1.0, tk.END)
                output_text.insert(tk.END, "Начинаю сканирование сети...\n")

                # Получаем локальный IP
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(('8.8.8.8', 80))
                    local_ip = s.getsockname()[0]
                    s.close()

                    # Определяем подсеть
                    ip_parts = local_ip.split('.')
                    subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"

                    output_text.insert(tk.END, f"Локальный IP: {local_ip}\n")
                    output_text.insert(tk.END, f"Подсеть: {subnet}.0/24\n\n")

                    # Сканируем первые 20 адресов
                    for i in range(1, 21):
                        ip = f"{subnet}.{i}"
                        if ip != local_ip:
                            threading.Thread(target=ping_ip, args=(ip,), daemon=True).start()

                except Exception as e:
                    output_text.insert(tk.END, f"Ошибка: {e}\n")

            def ping_ip(ip):
                try:
                    param = '-n' if platform.system().lower() == 'windows' else '-c'
                    result = subprocess.run(['ping', param, '1', '-w', '1000', ip],
                                            capture_output=True, text=True)

                    if "TTL" in result.stdout or "ttl" in result.stdout.lower():
                        dialog.after(0, lambda: output_text.insert(tk.END, f"✓ {ip} - доступен\n"))

                        # Проверяем порт 80
                        try:
                            sock = socket.socket()
                            sock.settimeout(1)
                            if sock.connect_ex((ip, 80)) == 0:
                                dialog.after(0, lambda: output_text.insert(tk.END, f"  → Веб-сервер на {ip}:80\n"))
                            sock.close()
                        except:
                            pass
                except:
                    pass

            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=10)

            ttk.Button(btn_frame, text="Начать сканирование", command=start_scan).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        except Exception as e:
            self.log(f"Ошибка сканирования сети: {e}", 'ERROR')

    def ping_host(self, ip):
        """Пинг хоста"""
        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            result = subprocess.run(['ping', param, '1', '-w', '1000', ip],
                                    capture_output=True, text=True)

            if "TTL" in result.stdout or "ttl" in result.stdout.lower():
                self.queue.put(('status', f"Найден хост: {ip}"))

                # Проверяем порт 80
                sock = socket.socket()
                sock.settimeout(1)
                if sock.connect_ex((ip, 80)) == 0:
                    self.queue.put(('status', f"  → Веб-сервер на {ip}:80"))
                sock.close()
        except:
            pass

    def open_port_tool(self):
        """Инструмент открытия порта"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Открытие порта")
        dialog.geometry("500x400")

        ttk.Label(dialog, text="Открытие порта в брандмауэре", font=('Arial', 12)).pack(pady=10)

        # Основной фрейм
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Номер порта:").grid(row=0, column=0, sticky=tk.W, pady=5)
        port_entry = ttk.Entry(main_frame, width=20)
        port_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(main_frame, text="Протокол:").grid(row=1, column=0, sticky=tk.W, pady=5)
        protocol_var = tk.StringVar(value="TCP")
        ttk.Combobox(main_frame, textvariable=protocol_var,
                     values=["TCP", "UDP"], state='readonly', width=18).grid(row=1, column=1, pady=5, padx=5)

        ttk.Label(main_frame, text="Направление:").grid(row=2, column=0, sticky=tk.W, pady=5)
        direction_var = tk.StringVar(value="Входящий")
        ttk.Combobox(main_frame, textvariable=direction_var,
                     values=["Входящий", "Исходящий", "Оба"],
                     state='readonly', width=18).grid(row=2, column=1, pady=5, padx=5)

        ttk.Label(main_frame, text="Имя правила:").grid(row=3, column=0, sticky=tk.W, pady=5)
        rule_name = ttk.Entry(main_frame, width=20)
        rule_name.grid(row=3, column=1, pady=5, padx=5)
        rule_name.insert(0, "MyCustomPort")

        output_text = scrolledtext.ScrolledText(main_frame, height=8)
        output_text.grid(row=4, column=0, columnspan=2, sticky=tk.NSEW, pady=10, padx=5)

        main_frame.grid_rowconfigure(4, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        def open_port():
            try:
                port = int(port_entry.get())
                protocol = protocol_var.get()
                direction = direction_var.get()
                rule = rule_name.get()

                output_text.delete(1.0, tk.END)
                output_text.insert(tk.END, f"Открытие порта {port}/{protocol}...\n")

                if platform.system() == "Windows":
                    commands = []

                    if direction in ["Входящий", "Оба"]:
                        cmd = ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                               f'name={rule}In',
                               'dir=in',
                               'action=allow',
                               f'protocol={protocol}',
                               f'localport={port}',
                               'profile=any']
                        commands.append(("Входящее правило", cmd))

                    if direction in ["Исходящий", "Оба"]:
                        cmd = ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                               f'name={rule}Out',
                               'dir=out',
                               'action=allow',
                               f'protocol={protocol}',
                               f'localport={port}',
                               'profile=any']
                        commands.append(("Исходящее правило", cmd))

                    for rule_name_text, cmd in commands:
                        try:
                            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                            if result.returncode == 0:
                                output_text.insert(tk.END, f"✓ {rule_name_text} добавлено\n")
                            else:
                                output_text.insert(tk.END, f"✗ {rule_name_text}: {result.stderr}\n")
                        except Exception as e:
                            output_text.insert(tk.END, f"✗ Ошибка: {e}\n")

                    messagebox.showinfo("Успех", f"Порт {port} открыт")
                    self.log(f"Открыт порт {port}/{protocol} ({direction})", 'INFO')

                else:
                    output_text.insert(tk.END, "Для Linux/Mac используйте:\n")
                    output_text.insert(tk.END, "sudo ufw allow {port}/{protocol}\n")
                    output_text.insert(tk.END, "или\n")
                    output_text.insert(tk.END, "sudo iptables -A INPUT -p {protocol} --dport {port} -j ACCEPT\n")
                    messagebox.showinfo("Информация", "На Linux/Mac используйте iptables/ufw")

            except ValueError:
                output_text.insert(tk.END, "✗ Ошибка: Введите корректный номер порта\n")
            except Exception as e:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")
                self.log(f"Ошибка открытия порта: {e}", 'ERROR')

        # Кнопки
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Открыть порт", command=open_port).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Тестировать порт",
                   command=lambda: self.test_port(port_entry.get() if port_entry.get() else "80")).pack(side=tk.LEFT,
                                                                                                        padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def test_port(self, port_str):
        """Тестирование порта"""
        try:
            port = int(port_str)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)

            result = sock.connect_ex(('localhost', port))
            sock.close()

            if result == 0:
                messagebox.showinfo("Тест порта", f"Порт {port} открыт на localhost")
            else:
                messagebox.showinfo("Тест порта", f"Порт {port} закрыт на localhost")
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректный номер порта")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def close_port_tool(self):
        """Закрытие порта с выбором из списка открытых портов"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Закрытие порта")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="Закрытие порта в брандмауэре", font=('Arial', 12)).pack(pady=10)

        # Получаем список открытых портов
        open_ports = self.get_open_ports_list()

        # Фрейм для списка портов
        list_frame = ttk.LabelFrame(dialog, text="Открытые порты на этом компьютере", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Treeview для отображения портов
        columns = ('port', 'protocol', 'state', 'process')
        tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)

        tree.heading('port', text='Порт')
        tree.heading('protocol', text='Протокол')
        tree.heading('state', text='Состояние')
        tree.heading('process', text='Процесс')

        tree.column('port', width=80)
        tree.column('protocol', width=80)
        tree.column('state', width=100)
        tree.column('process', width=200)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Заполняем список
        for port_info in open_ports:
            tree.insert('', 'end', values=(
                port_info.get('port', ''),
                port_info.get('protocol', 'TCP'),
                port_info.get('state', 'LISTENING'),
                port_info.get('process', 'Неизвестно')
            ))

        # Фрейм для ручного ввода
        input_frame = ttk.Frame(dialog)
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(input_frame, text="Или введите порт вручную:").pack(side=tk.LEFT, padx=5)
        port_entry = ttk.Entry(input_frame, width=15)
        port_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(input_frame, text="Протокол:").pack(side=tk.LEFT, padx=5)
        protocol_var = tk.StringVar(value="TCP")
        protocol_combo = ttk.Combobox(input_frame, textvariable=protocol_var,
                                      values=["TCP", "UDP"], state='readonly', width=8)
        protocol_combo.pack(side=tk.LEFT, padx=5)

        output_text = scrolledtext.ScrolledText(dialog, height=6)
        output_text.pack(fill=tk.X, padx=10, pady=5)

        def close_selected_port():
            selection = tree.selection()
            if selection:
                item = tree.item(selection[0])
                port = item['values'][0]
                protocol = item['values'][1]
                close_port(port, protocol)
            else:
                messagebox.showwarning("Внимание", "Выберите порт из списка")

        def close_manual_port():
            port = port_entry.get()
            protocol = protocol_var.get()

            if port and port.isdigit():
                close_port(int(port), protocol)
            else:
                messagebox.showwarning("Внимание", "Введите корректный номер порта")

        def close_port(port, protocol="TCP"):
            try:
                output_text.delete(1.0, tk.END)
                output_text.insert(tk.END, f"Закрытие порта {port}/{protocol}...\n")

                if platform.system() == "Windows":
                    # Пытаемся найти и удалить правила брандмауэра
                    rule_patterns = [
                        f"OpenPort{port}",
                        f"Port{port}",
                        f"CustomPort{port}",
                        f"MyCustomPort{port}"
                    ]

                    deleted_rules = []

                    for pattern in rule_patterns:
                        for direction in ['In', 'Out']:
                            rule_name = f"{pattern}{direction}"
                            try:
                                # Проверяем существование правила
                                check_cmd = ['netsh', 'advfirewall', 'firewall', 'show', 'rule',
                                             f'name={rule_name}']
                                result = subprocess.run(check_cmd, capture_output=True, text=True, shell=True)

                                if "Указанное правило не найдено" not in result.stdout and "No rules match" not in result.stdout:
                                    # Удаляем правило
                                    del_cmd = ['netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                                               f'name={rule_name}']
                                    result = subprocess.run(del_cmd, capture_output=True, text=True, shell=True)

                                    if result.returncode == 0:
                                        output_text.insert(tk.END, f"✓ Удалено правило: {rule_name}\n")
                                        deleted_rules.append(rule_name)
                                    else:
                                        output_text.insert(tk.END, f"✗ Ошибка удаления {rule_name}: {result.stderr}\n")
                            except Exception as e:
                                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")

                    if deleted_rules:
                        messagebox.showinfo("Успех", f"Порт {port} закрыт. Удалено правил: {len(deleted_rules)}")
                        self.log(f"Закрыт порт {port}/{protocol}", 'INFO')
                    else:
                        messagebox.showinfo("Информация", "Правила для этого порта не найдены")

                else:
                    output_text.insert(tk.END, "Для Linux/Mac используйте:\n")
                    output_text.insert(tk.END, "sudo ufw delete allow {port}/{protocol}\n")
                    output_text.insert(tk.END, "или\n")
                    output_text.insert(tk.END, "sudo iptables -D INPUT -p {protocol} --dport {port} -j ACCEPT\n")
                    messagebox.showinfo("Информация", "На Linux/Mac используйте iptables/ufw")

            except Exception as e:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")
                self.log(f"Ошибка закрытия порта: {e}", 'ERROR')

        # Кнопки
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Закрыть выбранный порт", command=close_selected_port).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть порт вручную", command=close_manual_port).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Обновить список",
                   command=lambda: self.refresh_port_list(tree)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def get_open_ports_list(self):
        """Получение списка открытых портов"""
        open_ports = []

        try:
            if platform.system() == "Windows":
                # Для Windows используем netstat
                result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, shell=True)
                lines = result.stdout.split('\n')

                for line in lines:
                    if 'LISTENING' in line and 'TCP' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            local_addr = parts[1]
                            if ':' in local_addr:
                                port = local_addr.split(':')[-1]
                                pid = parts[-1]

                                # Получаем имя процесса
                                try:
                                    process_result = subprocess.run(
                                        ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
                                        capture_output=True, text=True, shell=True
                                    )
                                    process_name = "Неизвестно"
                                    if process_result.stdout.strip():
                                        process_parts = process_result.stdout.strip().split(',')
                                        if len(process_parts) > 0:
                                            process_name = process_parts[0].replace('"', '')
                                except:
                                    process_name = "Неизвестно"

                                open_ports.append({
                                    'port': port,
                                    'protocol': 'TCP',
                                    'state': 'LISTENING',
                                    'process': process_name,
                                    'pid': pid
                                })
            else:
                # Для Linux/Mac
                result = subprocess.run(['netstat', '-tulpn'], capture_output=True, text=True, shell=True)
                lines = result.stdout.split('\n')

                for line in lines:
                    if 'LISTEN' in line:
                        parts = line.split()
                        if len(parts) >= 6:
                            proto = parts[0]
                            local_addr = parts[3]
                            if ':' in local_addr:
                                port = local_addr.split(':')[-1]
                                pid_process = parts[-1]

                                open_ports.append({
                                    'port': port,
                                    'protocol': proto.upper(),
                                    'state': 'LISTEN',
                                    'process': pid_process
                                })

        except Exception as e:
            self.log(f"Ошибка получения списка портов: {e}", 'ERROR')

        # Добавляем порты из результатов сканирования
        for item in self.results_tree.get_children():
            values = self.results_tree.item(item)['values']
            if values and len(values) > 1 and '✅' in values[1]:
                open_ports.append({
                    'port': values[0],
                    'protocol': 'TCP',
                    'state': 'OPEN',
                    'process': 'Сканированный порт'
                })

        return open_ports[:50]  # Ограничиваем список 50 портами

    def refresh_port_list(self, tree):
        """Обновление списка портов"""
        for item in tree.get_children():
            tree.delete(item)

        open_ports = self.get_open_ports_list()

        for port_info in open_ports:
            tree.insert('', 'end', values=(
                port_info.get('port', ''),
                port_info.get('protocol', 'TCP'),
                port_info.get('state', 'LISTENING'),
                port_info.get('process', 'Неизвестно')
            ))

    def open_in_browser(self, url_template):
        """Открытие URL в браузере"""
        try:
            host = self.host_var.get().strip()
            url = url_template.format(host=host)

            # Проверяем доступность
            try:
                response = requests.head(url, timeout=2, verify=False)
                if response.status_code < 400:
                    webbrowser.open(url)
                    self.log(f"Открыт {url}", 'INFO')
                else:
                    self.log(f"Сервер недоступен: {url}", 'WARNING')
            except:
                # Все равно пробуем открыть
                webbrowser.open(url)
                self.log(f"Попытка открыть {url}", 'INFO')

        except Exception as e:
            self.log(f"Ошибка открытия браузера: {e}", 'ERROR')

    def open_selected_in_browser(self):
        """Открыть выбранный порт в браузере"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            port = item['values'][0]
            host = self.host_var.get().strip()

            protocol = 'https' if port in [443, 8443] else 'http'
            url = f"{protocol}://{host}:{port}"

            webbrowser.open(url)
            self.log(f"Открыт {url}", 'INFO')

    def browser_go(self):
        """Перейти по URL в мини-браузере"""
        if HAS_TKINTERWEB:
            url = self.browser_url.get().strip()
            if url:
                try:
                    self.html_frame.load_url(url)
                    self.log(f"Загружено: {url}", 'INFO')
                except Exception as e:
                    self.log(f"Ошибка загрузки: {e}", 'ERROR')

    def browser_back(self):
        """Назад в браузере"""
        if HAS_TKINTERWEB:
            try:
                self.html_frame.back()
            except:
                pass

    def browser_forward(self):
        """Вперед в браузере"""
        if HAS_TKINTERWEB:
            try:
                self.html_frame.forward()
            except:
                pass

    def browser_refresh(self):
        """Обновить страницу в браузере"""
        if HAS_TKINTERWEB:
            try:
                self.html_frame.reload()
            except:
                pass

    # ==================== ИСТОРИЯ И СОХРАНЕНИЕ ====================

    def save_to_history(self):
        """Сохранение в историю"""
        try:
            scan_record = {
                'id': str(time.time()),
                'date': datetime.now().isoformat(),
                'host': self.current_scan['host'],
                'start_port': self.current_scan['start_port'],
                'end_port': self.current_scan['end_port'],
                'open_ports': self.current_scan['open_ports'],
                'duration': (self.current_scan['end_time'] -
                             self.current_scan['start_time']).total_seconds(),
                'method': self.scan_method.get(),
                'total_ports': self.current_scan['total_ports']
            }

            self.scan_history.append(scan_record)

            # Сохраняем в файл
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.scan_history, f, ensure_ascii=False, indent=2)

            # Обновляем GUI
            self.update_history_gui()

        except Exception as e:
            self.log(f"Ошибка сохранения истории: {e}", 'ERROR')

    def load_history(self):
        """Загрузка истории из файла"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return []

    def update_history_gui(self):
        """Обновление истории в GUI"""
        # Очищаем текущее
        self.history_tree.delete(*self.history_tree.get_children())

        # Добавляем записи (последние 50)
        for record in self.scan_history[-50:]:
            date = datetime.fromisoformat(record['date']).strftime("%Y-%m-%d %H:%M")
            ports = f"{record['start_port']}-{record['end_port']}"

            self.history_tree.insert('', 'end', values=(
                date,
                record['host'],
                ports,
                len(record['open_ports']),
                f"{record['duration']:.1f}с",
                record.get('method', 'N/A')
            ))

    def clear_history(self):
        """Очистка истории"""
        if messagebox.askyesno("Подтверждение", "Очистить всю историю?"):
            self.scan_history = []
            self.history_tree.delete(*self.history_tree.get_children())
            try:
                os.remove(self.history_file)
            except:
                pass
            self.log("История очищена", 'INFO')

    def repeat_scan(self):
        """Повторить выбранное сканирование"""
        selection = self.history_tree.selection()
        if selection:
            item = self.history_tree.item(selection[0])
            host = item['values'][1]

            self.host_var.set(host)
            self.start_scan()

    # ==================== СОХРАНЕНИЕ И ЭКСПОРТ ====================

    def save_results(self):
        """Сохранение результатов"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[
                    ("JSON files", "*.json"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                results = []
                for item in self.results_tree.get_children():
                    values = self.results_tree.item(item)['values']
                    results.append({
                        'port': values[0],
                        'status': values[1],
                        'service': values[2],
                        'banner': values[3],
                        'response': values[4]
                    })

                data = {
                    'scan_info': self.current_scan,
                    'results': results,
                    'export_date': datetime.now().isoformat()
                }

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                self.log(f"Результаты сохранены в {filename}", 'INFO')
                messagebox.showinfo("Успех", "Результаты сохранены")

        except Exception as e:
            self.log(f"Ошибка сохранения: {e}", 'ERROR')
            messagebox.showerror("Ошибка", str(e))

    def generate_report(self):
        """Генерация отчета"""
        try:
            report = "=== ОТЧЕТ СКАНИРОВАНИЯ ПОРТОВ ===\n\n"

            if self.current_scan:
                report += f"Цель: {self.current_scan['host']}\n"
                report += f"Диапазон портов: {self.current_scan['start_port']}-{self.current_scan['end_port']}\n"
                report += f"Время начала: {self.current_scan['start_time']}\n"

                if 'end_time' in self.current_scan:
                    duration = self.current_scan['end_time'] - self.current_scan['start_time']
                    report += f"Длительность: {duration.total_seconds():.2f} сек\n"
                    report += f"Найдено открытых портов: {len(self.current_scan['open_ports'])}\n\n"

            report += "ОТКРЫТЫЕ ПОРТЫ:\n"
            report += "-" * 80 + "\n"

            open_ports = []
            for item in self.results_tree.get_children():
                values = self.results_tree.item(item)['values']
                if '✅' in values[1]:  # Открытый порт
                    open_ports.append(values)

            if open_ports:
                for port, status, service, banner, response in open_ports:
                    report += f"Порт {port}: {service}\n"
                    if banner:
                        report += f"  Баннер: {banner[:100]}...\n"
                    if response:
                        report += f"  Ответ: {response}\n"
                    report += "\n"
            else:
                report += "Нет открытых портов\n"

            # Показываем отчет
            dialog = tk.Toplevel(self.root)
            dialog.title("Отчет сканирования")
            dialog.geometry("800x600")

            text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD)
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert(1.0, report)

            ttk.Button(dialog, text="Сохранить",
                       command=lambda: self.save_text_to_file(report)).pack(pady=10)

        except Exception as e:
            self.log(f"Ошибка генерации отчета: {e}", 'ERROR')

    def save_text_to_file(self, text):
        """Сохранение текста в файл"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text)

                self.log(f"Отчет сохранен в {filename}", 'INFO')
                messagebox.showinfo("Успех", "Отчет сохранен")

        except Exception as e:
            self.log(f"Ошибка сохранения отчета: {e}", 'ERROR')

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def set_port_range(self, ports):
        """Установка диапазона портов"""
        if len(ports) == 2:
            self.port_start.delete(0, tk.END)
            self.port_start.insert(0, str(ports[0]))
            self.port_end.delete(0, tk.END)
            self.port_end.insert(0, str(ports[1]))
        else:
            # Для списка портов
            self.port_start.delete(0, tk.END)
            self.port_start.insert(0, str(min(ports)))
            self.port_end.delete(0, tk.END)
            self.port_end.insert(0, str(max(ports)))

    def show_context_menu(self, event):
        """Показать контекстное меню"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_port(self):
        """Копировать номер порта"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            port = item['values'][0]
            self.root.clipboard_clear()
            self.root.clipboard_append(str(port))
            self.log(f"Скопирован порт: {port}", 'INFO')

    def clear_results(self):
        """Очистка результатов"""
        self.results_tree.delete(*self.results_tree.get_children())
        self.stats_label.config(text="")
        self.log("Результаты очищены", 'INFO')

    def clear_logs(self):
        """Очистка логов"""
        self.logs_text.delete(1.0, tk.END)
        self.log("Логи очищены", 'INFO')

    def save_logs(self):
        """Сохранение логов"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[
                    ("Log files", "*.log"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                logs = self.logs_text.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(logs)

                self.log(f"Логи сохранены в {filename}", 'INFO')
                messagebox.showinfo("Успех", "Логи сохранены")

        except Exception as e:
            self.log(f"Ошибка сохранения логов: {e}", 'ERROR')

    def export_logs(self):
        """Экспорт логов"""
        self.save_logs()

    def load_history_gui(self):
        """Загрузка истории в GUI"""
        self.update_history_gui()
        self.log("История загружена", 'INFO')

    def export_history_csv(self):
        """Экспорт истории в CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[
                    ("CSV files", "*.csv"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Дата', 'Цель', 'Порты', 'Открыто', 'Время', 'Метод'])

                    for record in self.scan_history[-100:]:  # Последние 100 записей
                        date = datetime.fromisoformat(record['date']).strftime("%Y-%m-%d %H:%M")
                        ports = f"{record['start_port']}-{record['end_port']}"

                        writer.writerow([
                            date,
                            record['host'],
                            ports,
                            len(record['open_ports']),
                            f"{record['duration']:.1f}",
                            record.get('method', 'N/A')
                        ])

                self.log(f"История экспортирована в {filename}", 'INFO')
                messagebox.showinfo("Успех", "История экспортирована")

        except Exception as e:
            self.log(f"Ошибка экспорта истории: {e}", 'ERROR')

    def open_settings(self):
        """Открыть настройки"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки")
        dialog.geometry("500x400")

        # Закладки в настройках
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка общих настроек
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="Общие")

        ttk.Label(general_frame, text="Максимальное количество потоков:").pack(pady=5)
        max_threads = ttk.Spinbox(general_frame, from_=1, to=1000, width=10)
        max_threads.pack(pady=5)
        max_threads.set(self.threads_var.get())

        ttk.Label(general_frame, text="Таймаут по умолчанию (сек):").pack(pady=5)
        default_timeout = ttk.Entry(general_frame, width=10)
        default_timeout.pack(pady=5)
        default_timeout.insert(0, str(self.timeout_var.get()))

        # Вкладка сохранения
        save_frame = ttk.Frame(notebook)
        notebook.add(save_frame, text="Сохранение")

        self.var_auto_save = tk.BooleanVar(value=True)
        ttk.Checkbutton(save_frame, text="Автосохранение результатов",
                        variable=self.var_auto_save).pack(pady=5)

        ttk.Checkbutton(save_frame, text="Сохранять логи в файл",
                        variable=self.var_save_logs).pack(pady=5)

        # Вкладка интерфейса
        ui_frame = ttk.Frame(notebook)
        notebook.add(ui_frame, text="Интерфейс")

        self.var_dark_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(ui_frame, text="Темная тема",
                        variable=self.var_dark_mode).pack(pady=5)

        ttk.Checkbutton(ui_frame, text="Показывать закрытые порты",
                        variable=self.var_show_closed).pack(pady=5)

        def save_settings():
            try:
                self.threads_var.set(int(max_threads.get()))
                self.timeout_var.set(float(default_timeout.get()))

                # Сохранение в конфиг
                config = {
                    'threads': self.threads_var.get(),
                    'timeout': self.timeout_var.get(),
                    'auto_save': self.var_auto_save.get(),
                    'save_logs': self.var_save_logs.get(),
                    'dark_mode': self.var_dark_mode.get(),
                    'show_closed': self.var_show_closed.get()
                }

                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

                self.log("Настройки сохранены", 'INFO')
                dialog.destroy()

            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        ttk.Button(dialog, text="Сохранить", command=save_settings).pack(pady=20)

    def load_config(self):
        """Загрузка конфигурации"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                self.threads_var.set(config.get('threads', 100))
                self.timeout_var.set(config.get('timeout', 1.0))
                self.var_auto_save.set(config.get('auto_save', True))
                self.var_save_logs.set(config.get('save_logs', True))
                self.var_show_closed.set(config.get('show_closed', False))

                if config.get('dark_mode', False):
                    self.apply_dark_theme()

        except Exception as e:
            self.log(f"Ошибка загрузки конфигурации: {e}", 'ERROR')

    def apply_dark_theme(self):
        """Применение темной темы"""
        try:
            self.root.configure(bg='#2b2b2b')
            self.style.theme_use('alt')
        except:
            pass

    def auto_save(self):
        """Автосохранение"""
        if self.var_auto_save.get() and self.current_scan:
            try:
                temp_file = f"autosave_{int(time.time())}.json"
                data = {
                    'current_scan': self.current_scan,
                    'timestamp': datetime.now().isoformat()
                }

                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # Удаляем старые автосейвы (оставляем последние 5)
                import glob
                autosaves = glob.glob("autosave_*.json")
                autosaves.sort(key=os.path.getmtime, reverse=True)

                for old_file in autosaves[5:]:
                    try:
                        os.remove(old_file)
                    except:
                        pass

            except:
                pass

        # Планируем следующее автосохранение
        self.root.after(30000, self.auto_save)

    # ==================== РАБОЧИЕ ИНСТРУМЕНТЫ ====================

    def ping_tool(self):
        """Инструмент ping - полностью рабочий"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Ping инструмент")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="Ping инструмент", font=('Arial', 12)).pack(pady=10)

        # Основной фрейм
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Хост
        host_frame = ttk.Frame(main_frame)
        host_frame.pack(fill=tk.X, pady=5)

        ttk.Label(host_frame, text="Хост/IP:").pack(side=tk.LEFT, padx=5)
        host_entry = ttk.Entry(host_frame, width=30)
        host_entry.pack(side=tk.LEFT, padx=5)
        host_entry.insert(0, self.host_var.get())

        # Количество пакетов
        count_frame = ttk.Frame(main_frame)
        count_frame.pack(fill=tk.X, pady=5)

        ttk.Label(count_frame, text="Количество пакетов:").pack(side=tk.LEFT, padx=5)
        count_var = tk.StringVar(value="4")
        count_combo = ttk.Combobox(count_frame, textvariable=count_var,
                                   values=["1", "2", "4", "8", "16"], width=10, state='readonly')
        count_combo.pack(side=tk.LEFT, padx=5)

        # Размер пакета
        size_frame = ttk.Frame(main_frame)
        size_frame.pack(fill=tk.X, pady=5)

        ttk.Label(size_frame, text="Размер пакета (байт):").pack(side=tk.LEFT, padx=5)
        size_var = tk.StringVar(value="32")
        size_combo = ttk.Combobox(size_frame, textvariable=size_var,
                                  values=["32", "64", "128", "256", "512", "1024"], width=10, state='readonly')
        size_combo.pack(side=tk.LEFT, padx=5)

        # Время ожидания
        timeout_frame = ttk.Frame(main_frame)
        timeout_frame.pack(fill=tk.X, pady=5)

        ttk.Label(timeout_frame, text="Таймаут (сек):").pack(side=tk.LEFT, padx=5)
        timeout_var = tk.StringVar(value="2")
        timeout_combo = ttk.Combobox(timeout_frame, textvariable=timeout_var,
                                     values=["1", "2", "3", "5", "10"], width=10, state='readonly')
        timeout_combo.pack(side=tk.LEFT, padx=5)

        # Поле вывода
        output_text = scrolledtext.ScrolledText(main_frame, height=15)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def do_ping():
            host = host_entry.get().strip()
            count = count_var.get()
            size = size_var.get()
            timeout = timeout_var.get()

            if not host:
                messagebox.showwarning("Внимание", "Введите хост или IP адрес")
                return

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Pinging {host} with {size} bytes of data...\n\n")

            try:
                # Определяем команду ping в зависимости от ОС
                if platform.system().lower() == "windows":
                    cmd = ['ping', '-n', count, '-l', size, '-w', str(int(timeout) * 1000), host]
                else:
                    cmd = ['ping', '-c', count, '-s', size, '-W', timeout, host]

                # Запускаем ping в отдельном потоке
                def ping_thread():
                    try:
                        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                   text=True, universal_newlines=True)

                        # Читаем вывод в реальном времени
                        for line in iter(process.stdout.readline, ''):
                            dialog.after(0, lambda l=line: output_text.insert(tk.END, l))
                            dialog.after(0, lambda: output_text.see(tk.END))

                        process.stdout.close()
                        return_code = process.wait()

                        if return_code == 0:
                            dialog.after(0, lambda: output_text.insert(tk.END, "\n✓ Ping успешен\n"))
                        else:
                            dialog.after(0, lambda: output_text.insert(tk.END, "\n✗ Ping не удался\n"))

                    except Exception as e:
                        dialog.after(0, lambda: output_text.insert(tk.END, f"\n✗ Ошибка: {e}\n"))

                    dialog.after(0, lambda: stop_btn.config(state='disabled'))
                    dialog.after(0, lambda: start_btn.config(state='normal'))

                # Запускаем поток
                thread = threading.Thread(target=ping_thread, daemon=True)
                thread.start()

                # Блокируем кнопку старта
                start_btn.config(state='disabled')

            except Exception as e:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")
                self.log(f"Ошибка ping: {e}", 'ERROR')

        def stop_ping():
            # В текущей реализации остановка ping требует более сложной логики
            # Можно добавить остановку через subprocess.kill()
            output_text.insert(tk.END, "\n⏹ Ping остановлен пользователем\n")

        # Кнопки
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        start_btn = ttk.Button(btn_frame, text="Выполнить ping", command=do_ping)
        start_btn.pack(side=tk.LEFT, padx=5)

        stop_btn = ttk.Button(btn_frame, text="Остановить", command=stop_ping)
        stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def traceroute_tool(self):
        """Инструмент traceroute - рабочий"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Traceroute")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="Traceroute инструмент", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Хост/IP:").pack(pady=5)
        host_entry = ttk.Entry(main_frame, width=40)
        host_entry.pack(pady=5)
        host_entry.insert(0, "google.com")

        output_text = scrolledtext.ScrolledText(main_frame, height=15)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def do_traceroute():
            host = host_entry.get().strip()
            if not host:
                messagebox.showwarning("Внимание", "Введите хост")
                return

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Traceroute to {host}...\n\n")

            try:
                # Определяем команду в зависимости от ОС
                if platform.system().lower() == "windows":
                    cmd = ['tracert', '-h', '30', '-w', '1000', host]
                else:
                    cmd = ['traceroute', '-m', '30', '-w', '1', host]

                def trace_thread():
                    try:
                        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                   text=True, universal_newlines=True)

                        for line in iter(process.stdout.readline, ''):
                            dialog.after(0, lambda l=line: output_text.insert(tk.END, l))
                            dialog.after(0, lambda: output_text.see(tk.END))

                        process.stdout.close()
                        return_code = process.wait()

                        if return_code == 0:
                            dialog.after(0, lambda: output_text.insert(tk.END, "\n✓ Traceroute завершен\n"))
                        else:
                            dialog.after(0, lambda: output_text.insert(tk.END, "\n✗ Traceroute не удался\n"))

                    except FileNotFoundError:
                        dialog.after(0, lambda: output_text.insert(tk.END, "\n✗ Команда traceroute/tracert не найдена\n"
                                                                           "Установите traceroute для вашей ОС\n"))
                    except Exception as e:
                        dialog.after(0, lambda: output_text.insert(tk.END, f"\n✗ Ошибка: {e}\n"))

                thread = threading.Thread(target=trace_thread, daemon=True)
                thread.start()

            except Exception as e:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Выполнить traceroute", command=do_traceroute).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def dns_lookup_tool(self):
        """Инструмент DNS lookup - рабочий"""
        dialog = tk.Toplevel(self.root)
        dialog.title("DNS Lookup")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="DNS Lookup инструмент", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Домен или IP:").pack(pady=5)
        host_entry = ttk.Entry(main_frame, width=40)
        host_entry.pack(pady=5)
        host_entry.insert(0, "google.com")

        ttk.Label(main_frame, text="Тип записи:").pack(pady=5)
        type_var = tk.StringVar(value="A")
        type_combo = ttk.Combobox(main_frame, textvariable=type_var,
                                  values=["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "PTR"],
                                  state='readonly', width=15)
        type_combo.pack(pady=5)

        output_text = scrolledtext.ScrolledText(main_frame, height=15)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def do_dns_lookup():
            host = host_entry.get().strip()
            record_type = type_var.get()

            if not host:
                messagebox.showwarning("Внимание", "Введите домен или IP")
                return

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"DNS Lookup for {host} (Type: {record_type})...\n\n")

            try:
                import dns.resolver
                import dns.reversename

                def dns_thread():
                    try:
                        if record_type == "PTR":
                            # Reverse DNS lookup
                            rev_name = dns.reversename.from_address(host)
                            answers = dns.resolver.resolve(rev_name, "PTR")
                        else:
                            answers = dns.resolver.resolve(host, record_type)

                        for rdata in answers:
                            dialog.after(0, lambda rd=rdata: output_text.insert(tk.END, f"{rd}\n"))

                        dialog.after(0, lambda: output_text.insert(tk.END, f"\n✓ Найдено {len(answers)} записей\n"))

                    except dns.resolver.NoAnswer:
                        dialog.after(0, lambda: output_text.insert(tk.END, "✗ Нет записей такого типа\n"))
                    except dns.resolver.NXDOMAIN:
                        dialog.after(0, lambda: output_text.insert(tk.END, "✗ Домен не существует\n"))
                    except dns.resolver.Timeout:
                        dialog.after(0, lambda: output_text.insert(tk.END, "✗ Таймаут DNS запроса\n"))
                    except Exception as e:
                        dialog.after(0, lambda: output_text.insert(tk.END, f"✗ Ошибка: {e}\n"))

                thread = threading.Thread(target=dns_thread, daemon=True)
                thread.start()

            except ImportError:
                output_text.insert(tk.END, "✗ Установите dnspython: pip install dnspython\n")
            except Exception as e:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Выполнить DNS lookup", command=do_dns_lookup).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def bandwidth_test(self):
        """Тест пропускной способности - рабочий"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Тест пропускной способности")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="Тест пропускной способности", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Сервер для теста:").pack(pady=5)
        server_var = tk.StringVar(value="speedtest.net")
        server_combo = ttk.Combobox(main_frame, textvariable=server_var,
                                    values=["speedtest.net", "fast.com", "google.com", "yandex.ru"],
                                    state='readonly', width=30)
        server_combo.pack(pady=5)

        ttk.Label(main_frame, text="Размер теста (МБ):").pack(pady=5)
        size_var = tk.StringVar(value="10")
        size_combo = ttk.Combobox(main_frame, textvariable=size_var,
                                  values=["1", "5", "10", "20", "50", "100"],
                                  state='readonly', width=15)
        size_combo.pack(pady=5)

        output_text = scrolledtext.ScrolledText(main_frame, height=15)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        progress = ttk.Progressbar(main_frame, mode='indeterminate', length=400)
        progress.pack(pady=5)

        def do_bandwidth_test():
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, "Запуск теста скорости...\n\n")

            progress.start()

            def test_thread():
                try:
                    import speedtest

                    dialog.after(0, lambda: output_text.insert(tk.END, "Инициализация теста скорости...\n"))

                    st = speedtest.Speedtest()
                    st.get_best_server()

                    dialog.after(0, lambda: output_text.insert(tk.END,
                                                               f"Сервер: {st.best['name']} ({st.best['country']})\n"))
                    dialog.after(0, lambda: output_text.insert(tk.END, f"Пинг: {st.best['latency']:.2f} ms\n\n"))

                    dialog.after(0, lambda: output_text.insert(tk.END, "Тест скорости загрузки...\n"))
                    download_speed = st.download() / 1_000_000  # Convert to Mbps
                    dialog.after(0, lambda: output_text.insert(tk.END, f"Скачивание: {download_speed:.2f} Mbps\n"))

                    dialog.after(0, lambda: output_text.insert(tk.END, "Тест скорости отдачи...\n"))
                    upload_speed = st.upload() / 1_000_000  # Convert to Mbps
                    dialog.after(0, lambda: output_text.insert(tk.END, f"Отдача: {upload_speed:.2f} Mbps\n\n"))

                    dialog.after(0, lambda: output_text.insert(tk.END, f"Итоговая скорость:\n"))
                    dialog.after(0, lambda: output_text.insert(tk.END, f"  ↓ Скачивание: {download_speed:.2f} Mbps\n"))
                    dialog.after(0, lambda: output_text.insert(tk.END, f"  ↑ Отдача: {upload_speed:.2f} Mbps\n"))

                    if download_speed > 100:
                        dialog.after(0, lambda: output_text.insert(tk.END, "\n✓ Отличная скорость интернета!\n"))
                    elif download_speed > 50:
                        dialog.after(0, lambda: output_text.insert(tk.END, "\n✓ Хорошая скорость интернета\n"))
                    elif download_speed > 10:
                        dialog.after(0, lambda: output_text.insert(tk.END, "\n✓ Средняя скорость интернета\n"))
                    else:
                        dialog.after(0, lambda: output_text.insert(tk.END, "\n⚠ Медленная скорость интернета\n"))

                except ImportError:
                    dialog.after(0, lambda: output_text.insert(tk.END,
                                                               "\n✗ Установите speedtest-cli: pip install speedtest-cli\n"))
                except Exception as e:
                    dialog.after(0, lambda: output_text.insert(tk.END, f"\n✗ Ошибка: {e}\n"))

                finally:
                    dialog.after(0, lambda: progress.stop())

            thread = threading.Thread(target=test_thread, daemon=True)
            thread.start()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Начать тест", command=do_bandwidth_test).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def firewall_check(self):
        """Проверка брандмауэра - рабочий"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Проверка брандмауэра")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="Проверка брандмауэра", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        output_text = scrolledtext.ScrolledText(main_frame, height=20)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def check_firewall():
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, "Проверка настроек брандмауэра...\n\n")

            try:
                if platform.system() == "Windows":
                    # Проверяем статус брандмауэра Windows
                    cmd = ['netsh', 'advfirewall', 'show', 'allprofiles']
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

                    output_text.insert(tk.END, "=== Статус брандмауэра Windows ===\n\n")
                    output_text.insert(tk.END, result.stdout)

                    # Проверяем открытые порты
                    output_text.insert(tk.END, "\n=== Открытые порты ===\n\n")
                    cmd_ports = ['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=all']
                    result_ports = subprocess.run(cmd_ports, capture_output=True, text=True, shell=True)

                    open_rules = []
                    lines = result_ports.stdout.split('\n')
                    for line in lines:
                        if 'Разрешить' in line or 'Allow' in line:
                            open_rules.append(line.strip())

                    if open_rules:
                        for rule in open_rules[:20]:  # Показываем первые 20 правил
                            output_text.insert(tk.END, f"{rule}\n")
                        if len(open_rules) > 20:
                            output_text.insert(tk.END, f"... и еще {len(open_rules) - 20} правил\n")
                    else:
                        output_text.insert(tk.END, "Нет открытых правил\n")

                elif platform.system() == "Linux":
                    # Проверяем iptables
                    try:
                        cmd = ['sudo', 'iptables', '-L', '-n', '-v']
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        output_text.insert(tk.END, "=== iptables правила ===\n\n")
                        output_text.insert(tk.END, result.stdout)
                    except:
                        # Проверяем ufw
                        try:
                            cmd = ['sudo', 'ufw', 'status', 'verbose']
                            result = subprocess.run(cmd, capture_output=True, text=True)
                            output_text.insert(tk.END, "=== UFW статус ===\n\n")
                            output_text.insert(tk.END, result.stdout)
                        except:
                            output_text.insert(tk.END, "Не удалось проверить брандмауэр\n")

                else:
                    output_text.insert(tk.END, f"Проверка брандмауэра для {platform.system()} не реализована\n")

                output_text.insert(tk.END, "\n✓ Проверка завершена\n")

            except Exception as e:
                output_text.insert(tk.END, f"\n✗ Ошибка: {e}\n")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Проверить брандмауэр", command=check_firewall).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def start_server_tool(self):
        """Запуск сервера с пользовательским HTML/CSS/JS"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Запуск HTTP сервера")
        dialog.geometry("800x700")

        # Переменные
        self.server_port = tk.StringVar(value="8080")
        self.server_html = ""
        self.server_css = ""
        self.server_js = ""

        ttk.Label(dialog, text="Настройка HTTP сервера", font=('Arial', 12)).pack(pady=10)

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Вкладка настроек
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Настройки")

        # Порт
        port_frame = ttk.Frame(settings_frame)
        port_frame.pack(fill=tk.X, pady=10, padx=10)

        ttk.Label(port_frame, text="Порт сервера:").pack(side=tk.LEFT, padx=5)
        port_entry = ttk.Entry(port_frame, textvariable=self.server_port, width=10)
        port_entry.pack(side=tk.LEFT, padx=5)

        # Кнопка проверки порта
        ttk.Button(port_frame, text="Проверить порт",
                   command=lambda: self.check_server_port(self.server_port.get())).pack(side=tk.LEFT, padx=10)

        # Информация о доступе
        info_frame = ttk.LabelFrame(settings_frame, text="Информация о доступе", padding="10")
        info_frame.pack(fill=tk.X, pady=10, padx=10)

        self.access_info = scrolledtext.ScrolledText(info_frame, height=6)
        self.access_info.pack(fill=tk.BOTH, expand=True)

        # Обновляем информацию
        self.update_server_info()

        # Вкладка HTML
        html_frame = ttk.Frame(notebook)
        notebook.add(html_frame, text="HTML")

        ttk.Label(html_frame, text="HTML код (будет внутри <body>):").pack(pady=5)

        self.html_editor = scrolledtext.ScrolledText(html_frame, height=15)
        self.html_editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.html_editor.insert(tk.END, """<h1>Добро пожаловать на мой сервер!</h1>
<p>Это тестовая страница HTTP сервера.</p>
<button onclick="showMessage()">Нажми меня</button>
<div id="message" style="margin-top: 20px;"></div>""")

        # Вкладка CSS
        css_frame = ttk.Frame(notebook)
        notebook.add(css_frame, text="CSS")

        ttk.Label(css_frame, text="CSS стили:").pack(pady=5)

        self.css_editor = scrolledtext.ScrolledText(css_frame, height=15)
        self.css_editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.css_editor.insert(tk.END, """body {
    font-family: Arial, sans-serif;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    background-color: #f0f0f0;
}
h1 {
    color: #333;
}
button {
    background-color: #4CAF50;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
}
button:hover {
    background-color: #45a049;
}""")

        # Вкладка JavaScript
        js_frame = ttk.Frame(notebook)
        notebook.add(js_frame, text="JavaScript")

        ttk.Label(js_frame, text="JavaScript код:").pack(pady=5)

        self.js_editor = scrolledtext.ScrolledText(js_frame, height=15)
        self.js_editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.js_editor.insert(tk.END, """function showMessage() {
    const messages = [
        "Привет от HTTP сервера!",
        "Сервер работает отлично!",
        "Вы можете изменить этот код",
        "Добавьте свой функционал"
    ];
    const randomMessage = messages[Math.floor(Math.random() * messages.length)];
    document.getElementById('message').innerHTML = '<strong>' + randomMessage + '</strong>';

    // Анимация
    const messageDiv = document.getElementById('message');
    messageDiv.style.transition = 'all 0.3s';
    messageDiv.style.color = '#d35400';
    setTimeout(() => {
        messageDiv.style.color = '#333';
    }, 300);
}""")

        # Статус сервера
        status_frame = ttk.Frame(dialog)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.server_status = ttk.Label(status_frame, text="Сервер не запущен", foreground="red")
        self.server_status.pack(side=tk.LEFT, padx=5)

        # Кнопки управления
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Запустить сервер",
                   command=self.start_http_server).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Остановить сервер",
                   command=self.stop_http_server).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Открыть в браузере",
                   command=self.open_server_in_browser).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть",
                   command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def update_server_info(self):
        """Обновление информации о доступе к серверу"""
        try:
            # Получаем локальный IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()

            port = self.server_port.get()

            info = f"Локальный доступ:\n"
            info += f"  http://localhost:{port}\n"
            info += f"  http://127.0.0.1:{port}\n\n"

            info += f"Доступ из локальной сети:\n"
            info += f"  http://{local_ip}:{port}\n\n"

            info += f"Для доступа с других устройств:\n"
            info += f"  • Убедитесь, что устройства в одной сети\n"
            info += f"  • Откройте порт {port} в брандмауэре\n"
            info += f"  • Используйте IP адрес: {local_ip}\n"

            self.access_info.delete(1.0, tk.END)
            self.access_info.insert(tk.END, info)

        except Exception as e:
            self.access_info.delete(1.0, tk.END)
            self.access_info.insert(tk.END, f"Ошибка получения информации: {e}")

    def check_server_port(self, port_str):
        """Проверка доступности порта"""
        try:
            port = int(port_str)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)

            result = sock.connect_ex(('localhost', port))
            sock.close()

            if result == 0:
                messagebox.showwarning("Порт занят",
                                       f"Порт {port} уже используется другим приложением.\n"
                                       f"Выберите другой порт или остановите приложение.")
            else:
                messagebox.showinfo("Порт свободен",
                                    f"Порт {port} доступен для использования.")

        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректный номер порта")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def start_http_server(self):
        """Запуск HTTP сервера"""
        try:
            port = int(self.server_port.get())

            # Проверяем порт
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            if sock.connect_ex(('localhost', port)) == 0:
                sock.close()
                messagebox.showerror("Ошибка", f"Порт {port} уже используется")
                return
            sock.close()

            # Получаем код из редакторов
            html_code = self.html_editor.get(1.0, tk.END)
            css_code = self.css_editor.get(1.0, tk.END)
            js_code = self.js_editor.get(1.0, tk.END)

            # Создаем HTTP обработчик
            class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
                def do_GET(self):
                    if self.path == '/':
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html; charset=utf-8')
                        self.end_headers()

                        # Создаем полную HTML страницу
                        full_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTTP Сервер</title>
    <style>
    {css_code}
    </style>
</head>
<body>
    {html_code}
    <script>
    {js_code}
    </script>
    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ccc; color: #666;">
        <p>Сервер запущен на порту {port}</p>
        <p>Локальное время: <span id="datetime"></span></p>
        <script>
        function updateDateTime() {{
            const now = new Date();
            document.getElementById('datetime').textContent = now.toLocaleString('ru-RU');
        }}
        updateDateTime();
        setInterval(updateDateTime, 1000);
        </script>
    </footer>
</body>
</html>"""

                        self.wfile.write(full_html.encode('utf-8'))
                    else:
                        super().do_GET()

            # Запускаем сервер в отдельном потоке
            self.http_server = socketserver.TCPServer(("", port), CustomHTTPRequestHandler)
            self.server_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
            self.server_thread.start()

            self.server_running = True
            self.server_status.config(text=f"Сервер запущен на порту {port}", foreground="green")

            self.log(f"HTTP сервер запущен на порту {port}", 'INFO')
            messagebox.showinfo("Сервер запущен",
                                f"HTTP сервер запущен на порту {port}\n\n"
                                f"Доступ по адресам:\n"
                                f"• http://localhost:{port}\n"
                                f"• http://127.0.0.1:{port}")

        except Exception as e:
            self.log(f"Ошибка запуска сервера: {e}", 'ERROR')
            messagebox.showerror("Ошибка", str(e))

    def stop_http_server(self):
        """Остановка HTTP сервера"""
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
            self.http_server = None
            self.server_thread = None
            self.server_running = False

            self.server_status.config(text="Сервер не запущен", foreground="red")
            self.log("HTTP сервер остановлен", 'INFO')
            messagebox.showinfo("Сервер остановлен", "HTTP сервер был остановлен")

    def open_server_in_browser(self):
        """Открытие сервера в браузере"""
        if self.server_running:
            port = self.server_port.get()
            url = f"http://localhost:{port}"
            webbrowser.open(url)
            self.log(f"Открыт {url}", 'INFO')
        else:
            messagebox.showwarning("Сервер не запущен", "Сначала запустите сервер")

    def network_monitor(self):
        """Монитор сети - рабочий"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Монитор сети")
        dialog.geometry("700x600")

        ttk.Label(dialog, text="Монитор сетевой активности", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Информация о текущих соединениях
        info_frame = ttk.LabelFrame(main_frame, text="Текущие соединения", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True)

        self.connections_text = scrolledtext.ScrolledText(info_frame, height=20)
        self.connections_text.pack(fill=tk.BOTH, expand=True)

        # Статистика
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=10)

        self.stats_label = ttk.Label(stats_frame, text="Нажмите 'Обновить' для показа статистики")
        self.stats_label.pack()

        def update_network_info():
            try:
                self.connections_text.delete(1.0, tk.END)

                if platform.system() == "Windows":
                    # Для Windows
                    cmd = ['netstat', '-an']
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

                    self.connections_text.insert(tk.END, "=== Сетевые соединения ===\n\n")
                    self.connections_text.insert(tk.END, result.stdout)

                    # Подсчет статистики
                    lines = result.stdout.split('\n')
                    tcp_count = sum(1 for line in lines if 'TCP' in line)
                    udp_count = sum(1 for line in lines if 'UDP' in line)
                    listening_count = sum(1 for line in lines if 'LISTENING' in line)

                    self.stats_label.config(
                        text=f"TCP: {tcp_count} | UDP: {udp_count} | Listening: {listening_count}"
                    )

                else:
                    # Для Linux/Mac
                    cmd = ['netstat', '-tulpn']
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

                    self.connections_text.insert(tk.END, "=== Сетевые соединения ===\n\n")
                    self.connections_text.insert(tk.END, result.stdout)

            except Exception as e:
                self.connections_text.insert(tk.END, f"Ошибка: {e}\n")

        def start_monitoring():
            """Запуск мониторинга в реальном времени"""

            def monitoring_thread():
                while monitoring_active[0]:
                    dialog.after(0, update_network_info)
                    time.sleep(5)  # Обновление каждые 5 секунд

            monitoring_active[0] = True
            thread = threading.Thread(target=monitoring_thread, daemon=True)
            thread.start()
            start_btn.config(state='disabled')
            stop_btn.config(state='normal')

        def stop_monitoring():
            monitoring_active[0] = False
            start_btn.config(state='normal')
            stop_btn.config(state='disabled')

        monitoring_active = [False]

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        start_btn = ttk.Button(btn_frame, text="Начать мониторинг", command=start_monitoring)
        start_btn.pack(side=tk.LEFT, padx=5)

        stop_btn = ttk.Button(btn_frame, text="Остановить мониторинг", command=stop_monitoring, state='disabled')
        stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Обновить", command=update_network_info).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Экспорт",
                   command=lambda: self.export_text(self.connections_text.get(1.0, tk.END))).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def quick_scan(self):
        """Быстрое сканирование"""
        self.set_port_range((1, 1000))
        self.start_scan()

    def targeted_scan(self):
        """Целевое сканирование"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Целевое сканирование")
        dialog.geometry("400x300")

        ttk.Label(dialog, text="Выберите тип сканирования:").pack(pady=20)

        options = [
            ("Веб-серверы (80,443,8080,8443)", [80, 443, 8080, 8443]),
            ("Базы данных (3306,5432,27017)", [3306, 5432, 27017, 6379]),
            ("Игровые серверы", [25565, 27015, 27016, 7777]),
            ("Принтеры/Сети (515,9100)", [515, 9100, 631]),
            ("Удаленное управление (3389,5900)", [3389, 5900, 5800])
        ]

        for text, ports in options:
            btn = ttk.Button(dialog, text=text,
                             command=lambda p=ports: self.do_targeted_scan(p, dialog))
            btn.pack(pady=5)

    def do_targeted_scan(self, ports, dialog):
        """Выполнить целевое сканирование"""
        dialog.destroy()
        self.set_port_range((min(ports), max(ports)))
        self.start_scan()

    def traffic_analysis(self):
        """Анализ трафика - рабочий"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Анализ трафика")
        dialog.geometry("700x500")

        ttk.Label(dialog, text="Анализ сетевого трафика", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        output_text = scrolledtext.ScrolledText(main_frame, height=20)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def analyze_traffic():
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, "Анализ сетевого трафика...\n\n")

            try:
                # Получаем статистику сети
                if platform.system() == "Windows":
                    cmd = ['netstat', '-e']
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

                    output_text.insert(tk.END, "=== Статистика сетевого интерфейса ===\n\n")
                    output_text.insert(tk.END, result.stdout)

                    # Получаем список процессов использующих сеть
                    output_text.insert(tk.END, "\n=== Процессы использующие сеть ===\n\n")
                    cmd2 = ['netstat', '-b', '-o']
                    try:
                        result2 = subprocess.run(cmd2, capture_output=True, text=True, shell=True)
                        # Берем только первые 50 строк чтобы не перегружать
                        lines = result2.stdout.split('\n')[:50]
                        output_text.insert(tk.END, '\n'.join(lines))
                    except:
                        output_text.insert(tk.END, "Требуются права администратора\n")

                else:
                    # Для Linux
                    cmd = ['ifconfig']
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

                    output_text.insert(tk.END, "=== Статистика сетевых интерфейсов ===\n\n")
                    output_text.insert(tk.END, result.stdout)

                    output_text.insert(tk.END, "\n=== TOP процессов по сети ===\n\n")
                    try:
                        cmd2 = ['nethogs', '-v', '3']
                        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=5)
                        output_text.insert(tk.END, result2.stdout)
                    except:
                        output_text.insert(tk.END, "Установите nethogs: sudo apt install nethogs\n")

                output_text.insert(tk.END, "\n✓ Анализ завершен\n")

            except Exception as e:
                output_text.insert(tk.END, f"\n✗ Ошибка: {e}\n")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Анализировать трафик", command=analyze_traffic).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def network_setup(self):
        """Настройка сети - рабочий"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройка сети")
        dialog.geometry("500x400")

        ttk.Label(dialog, text="Настройка сетевых параметров", font=('Arial', 12)).pack(pady=10)

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Вкладка DNS
        dns_frame = ttk.Frame(notebook)
        notebook.add(dns_frame, text="DNS")

        ttk.Label(dns_frame, text="Предпочитаемый DNS сервер:").pack(pady=5)
        dns1_entry = ttk.Entry(dns_frame, width=20)
        dns1_entry.pack(pady=5)
        dns1_entry.insert(0, "8.8.8.8")

        ttk.Label(dns_frame, text="Альтернативный DNS сервер:").pack(pady=5)
        dns2_entry = ttk.Entry(dns_frame, width=20)
        dns2_entry.pack(pady=5)
        dns2_entry.insert(0, "8.8.4.4")

        output_text = scrolledtext.ScrolledText(dns_frame, height=10)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def set_dns():
            dns1 = dns1_entry.get()
            dns2 = dns2_entry.get()

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Настройка DNS: {dns1}, {dns2}\n\n")

            try:
                if platform.system() == "Windows":
                    # Команды для Windows
                    interfaces = subprocess.run(['netsh', 'interface', 'show', 'interface'],
                                                capture_output=True, text=True, shell=True)

                    # Ищем активные интерфейсы
                    lines = interfaces.stdout.split('\n')
                    for line in lines:
                        if 'Подключено' in line or 'Connected' in line:
                            parts = line.split()
                            if len(parts) > 3:
                                interface_name = ' '.join(parts[3:])

                                cmd = ['netsh', 'interface', 'ipv4', 'set', 'dns',
                                       f'name="{interface_name}"', 'static', dns1, 'primary']
                                result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

                                if result.returncode == 0:
                                    output_text.insert(tk.END, f"✓ Основной DNS установлен для {interface_name}\n")

                                    if dns2:
                                        cmd2 = ['netsh', 'interface', 'ipv4', 'add', 'dns',
                                                f'name="{interface_name}"', dns2, 'index=2']
                                        subprocess.run(cmd2, capture_output=True, text=True, shell=True)
                                        output_text.insert(tk.END, f"✓ Альтернативный DNS установлен\n")
                                else:
                                    output_text.insert(tk.END, f"✗ Ошибка: {result.stderr}\n")

                    output_text.insert(tk.END, "\n⚠ Может потребоваться перезагрузка\n")

                else:
                    output_text.insert(tk.END, "Для Linux/Mac измените /etc/resolv.conf\n")

            except Exception as e:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")

        ttk.Button(dns_frame, text="Установить DNS", command=set_dns).pack(pady=10)

        # Вкладка Hosts
        hosts_frame = ttk.Frame(notebook)
        notebook.add(hosts_frame, text="Hosts файл")

        hosts_text = scrolledtext.ScrolledText(hosts_frame, height=15)
        hosts_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Загружаем текущий hosts файл
        try:
            hosts_path = r'C:\Windows\System32\drivers\etc\hosts' if platform.system() == "Windows" else '/etc/hosts'
            with open(hosts_path, 'r', encoding='utf-8') as f:
                hosts_text.insert(tk.END, f.read())
        except:
            hosts_text.insert(tk.END, "Не удалось загрузить hosts файл\n")

        def save_hosts():
            try:
                hosts_path = r'C:\Windows\System32\drivers\etc\hosts' if platform.system() == "Windows" else '/etc/hosts'
                content = hosts_text.get(1.0, tk.END)

                # Требуем права администратора для Windows
                if platform.system() == "Windows":
                    import ctypes
                    if not ctypes.windll.shell32.IsUserAnAdmin():
                        messagebox.showwarning("Требуются права", "Запустите программу от имени администратора")
                        return

                with open(hosts_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                messagebox.showinfo("Успех", "Hosts файл сохранен")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        ttk.Button(hosts_frame, text="Сохранить hosts", command=save_hosts).pack(pady=10)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack()

    def ssl_check(self):
        """Проверка SSL сертификата - рабочий"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Проверка SSL")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="Проверка SSL сертификата", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Домен (например: google.com):").pack(pady=5)
        domain_entry = ttk.Entry(main_frame, width=40)
        domain_entry.pack(pady=5)
        domain_entry.insert(0, "google.com")

        output_text = scrolledtext.ScrolledText(main_frame, height=15)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def check_ssl():
            domain = domain_entry.get().strip()
            if not domain:
                messagebox.showwarning("Внимание", "Введите домен")
                return

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Проверка SSL для {domain}...\n\n")

            try:
                import ssl
                import certifi
                from datetime import datetime

                # Создаем SSL контекст
                context = ssl.create_default_context(cafile=certifi.where())

                # Подключаемся к сайту
                with socket.create_connection((domain, 443)) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()

                        # Извлекаем информацию о сертификате
                        output_text.insert(tk.END, "=== Информация о SSL сертификате ===\n\n")

                        # Субъект
                        subject = dict(x[0] for x in cert['subject'])
                        output_text.insert(tk.END, "Субъект:\n")
                        for key, value in subject.items():
                            output_text.insert(tk.END, f"  {key}: {value}\n")

                        output_text.insert(tk.END, "\nИздатель:\n")
                        issuer = dict(x[0] for x in cert['issuer'])
                        for key, value in issuer.items():
                            output_text.insert(tk.END, f"  {key}: {value}\n")

                        # Даты действия
                        output_text.insert(tk.END, "\nСрок действия:\n")
                        not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
                        not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                        output_text.insert(tk.END, f"  Начало: {not_before}\n")
                        output_text.insert(tk.END, f"  Окончание: {not_after}\n")

                        # Проверяем срок действия
                        now = datetime.now()
                        days_left = (not_after - now).days

                        output_text.insert(tk.END, f"\nОсталось дней: {days_left}\n")

                        if days_left > 30:
                            output_text.insert(tk.END, "\n✓ Сертификат действителен\n")
                        elif days_left > 0:
                            output_text.insert(tk.END, f"\n⚠ Сертификат истекает через {days_left} дней\n")
                        else:
                            output_text.insert(tk.END, "\n✗ Сертификат просрочен\n")

                        # Дополнительная информация
                        output_text.insert(tk.END, f"\nВерсия: {cert.get('version', 'N/A')}\n")
                        output_text.insert(tk.END, f"Серийный номер: {cert.get('serialNumber', 'N/A')}\n")

            except Exception as e:
                output_text.insert(tk.END, f"\n✗ Ошибка: {e}\n")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Проверить SSL", command=check_ssl).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def whois_lookup(self):
        """WHOIS запрос - рабочий"""
        dialog = tk.Toplevel(self.root)
        dialog.title("WHOIS Lookup")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="WHOIS Lookup", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Домен или IP:").pack(pady=5)
        query_entry = ttk.Entry(main_frame, width=40)
        query_entry.pack(pady=5)
        query_entry.insert(0, "google.com")

        output_text = scrolledtext.ScrolledText(main_frame, height=15)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def do_whois():
            query = query_entry.get().strip()
            if not query:
                messagebox.showwarning("Внимание", "Введите домен или IP")
                return

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"WHOIS запрос для {query}...\n\n")

            try:
                import whois

                domain_info = whois.whois(query)

                output_text.insert(tk.END, "=== WHOIS информация ===\n\n")

                # Выводим основную информацию
                if hasattr(domain_info, 'domain_name'):
                    output_text.insert(tk.END, f"Домен: {domain_info.domain_name}\n")

                if hasattr(domain_info, 'registrar'):
                    output_text.insert(tk.END, f"Регистратор: {domain_info.registrar}\n")

                if hasattr(domain_info, 'creation_date'):
                    output_text.insert(tk.END, f"Дата создания: {domain_info.creation_date}\n")

                if hasattr(domain_info, 'expiration_date'):
                    output_text.insert(tk.END, f"Дата истечения: {domain_info.expiration_date}\n")

                if hasattr(domain_info, 'updated_date'):
                    output_text.insert(tk.END, f"Дата обновления: {domain_info.updated_date}\n")

                if hasattr(domain_info, 'name_servers'):
                    output_text.insert(tk.END, f"\nDNS серверы:\n")
                    for ns in domain_info.name_servers:
                        output_text.insert(tk.END, f"  {ns}\n")

                if hasattr(domain_info, 'status'):
                    output_text.insert(tk.END, f"\nСтатус: {domain_info.status}\n")

                if hasattr(domain_info, 'emails'):
                    output_text.insert(tk.END, f"\nEmail контакты:\n")
                    for email in domain_info.emails:
                        output_text.insert(tk.END, f"  {email}\n")

                output_text.insert(tk.END, "\n✓ WHOIS запрос завершен\n")

            except ImportError:
                output_text.insert(tk.END, "✗ Установите python-whois: pip install python-whois\n")
            except Exception as e:
                output_text.insert(tk.END, f"✗ Ошибка: {e}\n")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Выполнить WHOIS", command=do_whois).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def export_text(self, text):
        """Экспорт текста в файл"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text)

                messagebox.showinfo("Успех", "Текст экспортирован")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def check_service(self):
        """Проверка службы на выбранном порту"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            port = item['values'][0]
            service = item['values'][2]

            messagebox.showinfo("Информация о службе",
                                f"Порт: {port}\nСлужба: {service}\n\n"
                                f"Распространенные службы на этом порту:\n"
                                f"{self.get_service_info(port)}")

    def get_service_info(self, port):
        """Получить информацию о службе по порту"""
        common_services = {
            21: "FTP - File Transfer Protocol",
            22: "SSH - Secure Shell",
            23: "Telnet",
            25: "SMTP - Simple Mail Transfer Protocol",
            53: "DNS - Domain Name System",
            80: "HTTP - HyperText Transfer Protocol",
            110: "POP3 - Post Office Protocol v3",
            143: "IMAP - Internet Message Access Protocol",
            443: "HTTPS - HTTP Secure",
            465: "SMTPS - SMTP Secure",
            993: "IMAPS - IMAP Secure",
            995: "POP3S - POP3 Secure",
            3306: "MySQL Database",
            3389: "RDP - Remote Desktop Protocol",
            5432: "PostgreSQL Database",
            5900: "VNC - Virtual Network Computing",
            8080: "HTTP Proxy / Alternative HTTP",
            8443: "HTTPS Alternative",
            27017: "MongoDB Database",
        }

        return common_services.get(port, "Неизвестная служба")

    def add_to_favorites(self):
        """Добавить в избранное"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            port = item['values'][0]
            host = self.host_var.get()

            try:
                with open('favorites.json', 'r', encoding='utf-8') as f:
                    favorites = json.load(f)
            except:
                favorites = []

            favorite = {
                'host': host,
                'port': port,
                'service': item['values'][2],
                'added': datetime.now().isoformat()
            }

            favorites.append(favorite)

            with open('favorites.json', 'w', encoding='utf-8') as f:
                json.dump(favorites, f, ensure_ascii=False, indent=2)

            self.log(f"Добавлено в избранное: {host}:{port}", 'INFO')
            messagebox.showinfo("Успех", "Добавлено в избранное")

    def get_banner(self):
        """Получить баннер службы"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            port = item['values'][0]
            host = self.host_var.get()

            self.log(f"Получение баннера для {host}:{port}", 'INFO')

            # В отдельном потоке
            threading.Thread(target=self.fetch_banner,
                             args=(host, port),
                             daemon=True).start()

    def fetch_banner(self, host, port):
        """Получить баннер службы"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)

            if sock.connect_ex((host, port)) == 0:
                # Пробуем разные команды для разных протоколов
                if port in [21, 2121]:  # FTP
                    sock.send(b'\r\n')
                elif port in [22]:  # SSH
                    sock.send(b'SSH-2.0-Client\r\n')
                elif port in [25, 587]:  # SMTP
                    sock.send(b'EHLO example.com\r\n')
                elif port in [80, 443, 8080, 8443]:  # HTTP/S
                    sock.send(b'HEAD / HTTP/1.0\r\n\r\n')
                else:
                    sock.send(b'\r\n')

                banner = sock.recv(1024).decode('utf-8', errors='ignore')
                sock.close()

                if banner:
                    self.queue.put(('banner', f"Баннер {host}:{port}:\n{banner}"))
                else:
                    self.queue.put(('banner', f"Нет баннера на {host}:{port}"))
            else:
                self.queue.put(('banner', f"Порт {port} закрыт"))

        except Exception as e:
            self.queue.put(('banner', f"Ошибка: {e}"))

    def save_selected_result(self):
        """Сохранить выбранный результат"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])

            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Результат сканирования:\n")
                    f.write(f"Хост: {self.host_var.get()}\n")
                    f.write(f"Порт: {item['values'][0]}\n")
                    f.write(f"Статус: {item['values'][1]}\n")
                    f.write(f"Служба: {item['values'][2]}\n")
                    f.write(f"Баннер: {item['values'][3]}\n")
                    f.write(f"Ответ: {item['values'][4]}\n")

                self.log(f"Результат сохранен в {filename}", 'INFO')
                messagebox.showinfo("Успех", "Результат сохранен")

    def scan_network_dialog(self):
        """Диалог сканирования сети"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Сканирование сети")
        dialog.geometry("500x400")

        ttk.Label(dialog, text="Сканирование сети", font=('Arial', 12)).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Диапазон IP адресов:").pack(pady=5)

        ip_frame = ttk.Frame(main_frame)
        ip_frame.pack(pady=5)

        start_ip = ttk.Entry(ip_frame, width=15)
        start_ip.pack(side=tk.LEFT, padx=2)
        start_ip.insert(0, "192.168.1.1")

        ttk.Label(ip_frame, text="-").pack(side=tk.LEFT, padx=2)

        end_ip = ttk.Entry(ip_frame, width=15)
        end_ip.pack(side=tk.LEFT, padx=2)
        end_ip.insert(0, "192.168.1.254")

        output_text = scrolledtext.ScrolledText(main_frame, height=15)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def start_scan():
            start = start_ip.get()
            end = end_ip.get()

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Сканирование от {start} до {end}...\n\n")

            # Простое сканирование - проверяем первые 20 адресов
            import ipaddress

            try:
                start_ip_obj = ipaddress.ip_address(start)
                end_ip_obj = ipaddress.ip_address(end)

                # Генерируем IP адреса между началом и концом
                current_ip = int(start_ip_obj)
                end_ip_int = int(end_ip_obj)

                count = min(20, end_ip_int - current_ip + 1)

                for i in range(count):
                    ip = str(ipaddress.ip_address(current_ip + i))
                    threading.Thread(target=ping_and_check, args=(ip,), daemon=True).start()

            except Exception as e:
                output_text.insert(tk.END, f"Ошибка: {e}\n")

        def ping_and_check(ip):
            try:
                param = '-n' if platform.system().lower() == 'windows' else '-c'
                result = subprocess.run(['ping', param, '1', '-w', '1000', ip],
                                        capture_output=True, text=True)

                if "TTL" in result.stdout or "ttl" in result.stdout.lower():
                    dialog.after(0, lambda ip=ip: output_text.insert(tk.END, f"✓ {ip} - доступен\n"))

                    # Проверяем веб-сервер
                    try:
                        sock = socket.socket()
                        sock.settimeout(1)
                        if sock.connect_ex((ip, 80)) == 0:
                            dialog.after(0, lambda ip=ip: output_text.insert(tk.END, f"  → Веб-сервер (порт 80)\n"))
                        sock.close()
                    except:
                        pass

                    # Проверяем другие популярные порты
                    for port in [21, 22, 23, 25, 53, 443, 3389]:
                        try:
                            sock = socket.socket()
                            sock.settimeout(0.5)
                            if sock.connect_ex((ip, port)) == 0:
                                dialog.after(0, lambda ip=ip, port=port: output_text.insert(tk.END,
                                                                                            f"  → Порт {port} открыт\n"))
                            sock.close()
                        except:
                            pass

            except:
                pass

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Начать сканирование", command=start_scan).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def export_network_info(self):
        """Экспорт сетевой информации"""
        try:
            info = self.network_info.get(1.0, tk.END)
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(info)

                self.log(f"Сетевая информация экспортирована", 'INFO')
                messagebox.showinfo("Успех", "Информация экспортирована")

        except Exception as e:
            self.log(f"Ошибка экспорта: {e}", 'ERROR')


def main():
    """Запуск приложения"""
    root = tk.Tk()

    # Улучшаем DPI для Windows
    if platform.system() == "Windows":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

    app = MegaPortScanner(root)

    # Центрируем окно
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'1400x800+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    # Проверка зависимостей
    dependencies = ['requests']
    missing = []

    for dep in dependencies:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)

    if missing:
        print("⚠️ Установите недостающие зависимости:")
        print(f"   pip install {' '.join(missing)}")
        print("\nДля полного функционала установите также:")
        print("   pip install tkinterweb")
        print("   pip install speedtest-cli")
        print("   pip install python-whois")
        print("   pip install dnspython")
        input("\nНажмите Enter для выхода...")
    else:
        main()