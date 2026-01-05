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
import hashlib
from tkinter import simpledialog
import random

# Импорт инструментов
try:
    from advanced_scanner_tools import ScannerTools
except ImportError as e:
    print("Не найден файл advanced_scanner_tools.py")
    ScannerTools = None

# Импорт для мини-браузера
try:
    import tkinterweb
    HAS_TKINTERWEB = True
except ImportError:
    HAS_TKINTERWEB = False
    print("Для мини-браузера установите: pip install tkinterweb")
    tk.messagebox.showwarning("Импорт модуля", "Ошибка импорта: Для мини-браузера установите: pip install tkinterweb")



class MegaPortScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ Mega Port Scanner Pro")
        self.root.geometry("1400x800")

        # Инициализация инструментов
        self.tools = ScannerTools(self) if ScannerTools else None

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
        self.style.theme_use('clam')

        self.colors = {
            'open': '#2E7D32',
            'closed': '#757575',
            'error': '#D84315',
            'warning': '#FF8F00',
            'info': '#1565C0',
            'success': '#388E3C'
        }

        self.style.configure('Custom.TNotebook.Tab',
                             padding=[20, 5],
                             font=('Segoe UI', 10))

    def setup_gui(self):
        """Создание интерфейса"""
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.create_top_panel(main_container)
        self.create_center_area(main_container)
        self.create_bottom_panel(main_container)

    def create_top_panel(self, parent):
        """Верхняя панель с основными кнопками"""
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        title = ttk.Label(top_frame,
                          text="⚡ MEGA PORT SCANNER PRO",
                          font=('Segoe UI', 16, 'bold'))
        title.pack(side=tk.LEFT, padx=(0, 20))

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

    def create_center_area(self, parent):
        """Центральная область с вкладками"""
        self.notebook = ttk.Notebook(parent, style='Custom.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_scan = ttk.Frame(self.notebook)
        self.tab_network = ttk.Frame(self.notebook)
        self.tab_browser = ttk.Frame(self.notebook)
        self.tab_history = ttk.Frame(self.notebook)
        self.tab_logs = ttk.Frame(self.notebook)
        self.tab_tools = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_scan, text='📡 Сканирование')
        self.notebook.add(self.tab_network, text='🌐 Сеть')
        self.notebook.add(self.tab_browser, text='🌍 Браузер')
        self.notebook.add(self.tab_history, text='📊 История')
        self.notebook.add(self.tab_logs, text='📝 Логи')
        self.notebook.add(self.tab_tools, text='🛠 Инструменты')

        self.setup_scan_tab()
        self.setup_network_tab()
        self.setup_browser_tab()
        self.setup_history_tab()
        self.setup_logs_tab()
        self.setup_tools_tab()

    def setup_scan_tab(self):
        """Вкладка сканирования"""
        left_panel = ttk.LabelFrame(self.tab_scan, text="Настройки сканирования", padding="10")
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        ttk.Label(left_panel, text="Цель:").grid(row=0, column=0, sticky=tk.W, pady=5)

        host_frame = ttk.Frame(left_panel)
        host_frame.grid(row=0, column=1, sticky=tk.EW, pady=5)

        self.host_var = tk.StringVar(value="localhost")
        self.host_combo = ttk.Combobox(host_frame, textvariable=self.host_var, width=25)
        self.host_combo.grid(row=0, column=0)
        self.host_combo['values'] = ['localhost', '127.0.0.1', '192.168.1.1', '192.168.0.1']

        ttk.Button(host_frame, text="Сеть", command=self.scan_network_dialog).grid(row=0, column=1, padx=5)

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

        ttk.Label(left_panel, text="Метод:").grid(row=3, column=0, sticky=tk.W, pady=5)

        self.scan_method = ttk.Combobox(left_panel, values=[
            "Полное сканирование",
            "Быстрое сканирование",
            "Только известные порты",
            "Пинг + сканирование"
        ], state="readonly", width=25)
        self.scan_method.grid(row=3, column=1, sticky=tk.EW, pady=5)
        self.scan_method.set("Быстрое сканирование")

        ttk.Label(left_panel, text="Таймаут (сек):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.timeout_var = tk.DoubleVar(value=1.0)
        self.timeout_scale = ttk.Scale(left_panel, from_=0.1, to=5.0,
                                       variable=self.timeout_var, orient=tk.HORIZONTAL)
        self.timeout_scale.grid(row=4, column=1, sticky=tk.EW, pady=5)

        ttk.Label(left_panel, text="Потоки:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.threads_var = tk.IntVar(value=100)
        self.threads_spin = ttk.Spinbox(left_panel, from_=1, to=500,
                                        textvariable=self.threads_var, width=10)
        self.threads_spin.grid(row=5, column=1, sticky=tk.W, pady=5)

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

        right_panel = ttk.Frame(self.tab_scan)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        results_frame = ttk.LabelFrame(right_panel, text="Результаты сканирования", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('port', 'status', 'service', 'banner', 'response')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=20)

        self.results_tree.heading('port', text='Порт')
        self.results_tree.heading('status', text='Статус')
        self.results_tree.heading('service', text='Служба')
        self.results_tree.heading('banner', text='Баннер')
        self.results_tree.heading('response', text='Ответ')

        self.results_tree.column('port', width=80)
        self.results_tree.column('status', width=100)
        self.results_tree.column('service', width=150)
        self.results_tree.column('banner', width=200)
        self.results_tree.column('response', width=300)

        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)

        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.setup_context_menu()

        stats_frame = ttk.Frame(right_panel)
        stats_frame.pack(fill=tk.X, pady=(5, 0))

        self.stats_label = ttk.Label(stats_frame, text="Готов к сканированию")
        self.stats_label.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(stats_frame, mode='indeterminate', length=300)
        self.progress.pack(side=tk.RIGHT, padx=10)

    def setup_network_tab(self):
        """Вкладка информации о сети"""
        info_frame = ttk.LabelFrame(self.tab_network, text="Сетевая информация", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.network_info = scrolledtext.ScrolledText(info_frame, height=20)
        self.network_info.pack(fill=tk.BOTH, expand=True)

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

            self.html_frame = tkinterweb.HtmlFrame(browser_frame)
            self.html_frame.pack(fill=tk.BOTH, expand=True)
        else:
            ttk.Label(self.tab_browser,
                      text="Установите tkinterweb: pip install tkinterweb\n"
                           "Для просмотра веб-интерфейсов портов",
                      justify=tk.CENTER).pack(expand=True)

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

        columns = ('date', 'target', 'ports', 'open', 'duration', 'method')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings', height=20)

        self.history_tree.heading('date', text='Дата')
        self.history_tree.heading('target', text='Цель')
        self.history_tree.heading('ports', text='Порты')
        self.history_tree.heading('open', text='Открыто')
        self.history_tree.heading('duration', text='Время')
        self.history_tree.heading('method', text='Метод')

        self.history_tree.column('date', width=150)
        self.history_tree.column('target', width=150)
        self.history_tree.column('ports', width=100)
        self.history_tree.column('open', width=80)
        self.history_tree.column('duration', width=80)
        self.history_tree.column('method', width=120)

        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

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

        self.logs_text = scrolledtext.ScrolledText(logs_frame, height=30)
        self.logs_text.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.Frame(self.tab_logs)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(control_frame, text="Очистить логи",
                   command=self.clear_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Сохранить логи",
                   command=self.save_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Экспорт",
                   command=self.export_logs).pack(side=tk.LEFT, padx=2)

        ttk.Label(control_frame, text="Уровень:").pack(side=tk.LEFT, padx=(20, 5))
        self.log_level = ttk.Combobox(control_frame, values=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                                      state='readonly', width=10)
        self.log_level.pack(side=tk.LEFT)
        self.log_level.set('INFO')

    def setup_tools_tab(self):
        """Вкладка инструментов"""
        tools_frame = ttk.Frame(self.tab_tools)
        tools_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Создаем Notebook для группировки инструментов
        tools_notebook = ttk.Notebook(tools_frame)
        tools_notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладка 1: Основные инструменты
        basic_frame = ttk.Frame(tools_notebook)
        tools_notebook.add(basic_frame, text="Основные")

        # Вкладка 2: Сканирование сети
        scanning_frame = ttk.Frame(tools_notebook)
        tools_notebook.add(scanning_frame, text="Сканирование")

        # Вкладка 3: Безопасность
        security_frame = ttk.Frame(tools_notebook)
        tools_notebook.add(security_frame, text="Безопасность")

        # Вкладка 4: Анализ
        analysis_frame = ttk.Frame(tools_notebook)
        tools_notebook.add(analysis_frame, text="Анализ")

        # Вкладка 5: Дополнительно
        advanced_frame = ttk.Frame(tools_notebook)
        tools_notebook.add(advanced_frame, text="Дополнительно")

        if self.tools:
            # Основные инструменты
            basic_tools = [
                ("🔧 Открыть порт", self.tools.open_port_tool, 0, 0),
                ("🔒 Закрыть порт", self.tools.close_port_tool, 0, 1),
                ("📡 Ping хоста", self.tools.ping_tool, 1, 0),
                ("🌐 Traceroute", self.tools.traceroute_tool, 1, 1),
                ("🔍 DNS lookup", self.tools.dns_lookup_tool, 2, 0),
                ("📊 Пропускная способность", self.tools.bandwidth_test, 2, 1),
                ("🛡️ Проверка брандмауэра", self.tools.firewall_check, 3, 0),
                ("🚀 Запустить сервер", self.tools.start_server_tool, 3, 1),
            ]

            # Инструменты сканирования
            scanning_tools = [
                ("📶 Монитор сети", self.tools.network_monitor, 0, 0),
                ("⚡ Быстрый скан", self.tools.quick_scan, 0, 1),
                ("🎯 Целевое сканирование", self.tools.targeted_scan, 1, 0),
                ("📈 Анализ трафика", self.tools.traffic_analysis, 1, 1),
                ("🔧 Настройка сети", self.tools.network_setup, 2, 0),
                ("🔐 Проверка SSL", self.tools.ssl_check, 2, 1),
                ("📡 WHOIS запрос", self.tools.whois_lookup, 3, 0),
                ("🗺️ Карта сети", self.tools.network_mapper, 3, 1),
            ]

            # Инструменты безопасности
            security_tools = [
                ("⚠️ Сканер уязвимостей", self.tools.vulnerability_scanner, 0, 0),
                ("📡 Сниффер пакетов", self.tools.packet_sniffer, 0, 1),
                ("🌐 Сканер поддоменов", self.tools.subdomain_scanner, 1, 0),
                ("📶 Сканер Wi-Fi", self.tools.wifi_scanner, 1, 1),
                ("🔓 Тестер паролей", self.tools.password_cracker_tool, 2, 0),
            ]

            # Инструменты анализа
            analysis_tools = [
                ("📊 Проброс портов", self.tools.port_forwarding_tool, 0, 0),
                ("🔍 Анализ заголовков", self.analyze_headers_tool, 0, 1),
                ("📝 Генератор отчетов", self.report_generator, 1, 0),
                ("📊 Статистика сети", self.network_statistics, 1, 1),
            ]

            # Дополнительные инструменты
            advanced_tools = [
                ("⚙️ Настройки приложения", self.open_settings, 0, 0),
                ("💾 Резервное копирование", self.backup_config, 0, 1),
                ("🔄 Обновить базы", self.update_databases, 1, 0),
                ("📚 Справка", self.show_help, 1, 1),
                ("📜 УК РФ (Глава 28) (🔐)", self.show_law, 2, 0),
            ]

            # Создаем сетки для каждой вкладки
            for frame, tools_list in [
                (basic_frame, basic_tools),
                (scanning_frame, scanning_tools),
                (security_frame, security_tools),
                (analysis_frame, analysis_tools),
                (advanced_frame, advanced_tools)
            ]:
                for i in range(4):
                    frame.columnconfigure(i, weight=1)
                for i in range(8):
                    frame.rowconfigure(i, weight=1)

                for text, command, row, col in tools_list:
                    btn = ttk.Button(frame, text=text, command=command)
                    btn.grid(row=row, column=col, sticky=tk.NSEW, padx=5, pady=5, ipady=10)

        else:
            error_label = ttk.Label(tools_frame,
                                    text="⚠ Инструменты не загружены\nУбедитесь, что advanced_scanner_tools.py находится в той же папке",
                                    justify=tk.CENTER)
            error_label.pack(expand=True)

    def pe_get_wifi_info_pper(self):
        haggsh = "6d795f626573745f6d6163655f7076705f7065707065725f6c6f6f6b5f6f6e5f69745f6f5f6f5f67672e6d6163652e707670"
        return bytes.fromhex(haggsh).decode()

    def create_bottom_panel(self, parent):
        """Нижняя панель статуса"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(10, 0))

        self.status_var = tk.StringVar(value="Готов")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var,
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, ipady=5)

        info_frame = ttk.Frame(status_frame)
        info_frame.pack(fill=tk.X)

        self.scan_info = ttk.Label(info_frame, text="")
        self.scan_info.pack(side=tk.LEFT)

        self.time_label = ttk.Label(info_frame, text="")
        self.time_label.pack(side=tk.RIGHT)

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

        self.results_tree.bind("<Button-3>", self.show_context_menu)

    # ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

    def log(self, message, level='INFO'):
        """Логирование"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        self.logs_text.insert(tk.END, log_entry)
        self.logs_text.see(tk.END)

        if self.var_save_logs.get():
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
            except Exception as e:
                print(f"Error in log(): {e}")
                self.log(e)

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
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
                interfaces.append(('Основной', local_ip))
            finally:
                s.close()

            hostname = socket.gethostname()
            all_ips = socket.gethostbyname_ex(hostname)[2]

            for i, ip in enumerate(all_ips):
                if ip != local_ip and not ip.startswith('127.'):
                    interfaces.append((f"IP {i + 1}", ip))

        except Exception as e:
            self.log(f"Ошибка получения интерфейсов: {e}", 'ERROR')
            print(f"Error in get_network_interfaces(): {e}")

        return interfaces

    def update_network_info(self):
        """Обновление информации о сети"""
        try:
            info = "=== СЕТЕВАЯ ИНФОРМАЦИЯ ===\n\n"

            hostname = socket.gethostname()
            info += f"Имя компьютера: {hostname}\n"

            info += "\nIP адреса:\n"
            interfaces = self.get_network_interfaces()

            for iface_name, ip in interfaces:
                if not ip.startswith('127.'):
                    info += f"  {iface_name}: {ip}\n"

            info += "\nВнешний IP:\n"
            try:
                response = requests.get('https://api.ipify.org?format=json', timeout=5)
                if response.status_code == 200:
                    external_ip = response.json()['ip']
                    info += f"  {external_ip}\n"
            except Exception as e:
                info += "  Не удалось определить\n"
                print(f"Error in update_network_info(): {e}")
                self.log(e)

            info += f"\nОперационная система: {platform.system()} {platform.release()}\n"
            info += f"Архитектура: {platform.machine()}\n"

            self.network_info.delete(1.0, tk.END)
            self.network_info.insert(1.0, info)

        except Exception as e:
            self.log(f"Ошибка получения сетевой информации: {e}", 'ERROR')
            print(f"Error in update_network_info(): {e}")

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

            self.results_tree.delete(*self.results_tree.get_children())

            self.scanning = True
            self.current_scan = {
                'host': host,
                'start_port': start_port,
                'end_port': end_port,
                'start_time': datetime.now(),
                'open_ports': [],
                'total_ports': end_port - start_port + 1
            }

            self.progress.start()
            self.status_var.set(f"Сканирование {host}...")

            self.scan_thread = threading.Thread(target=self.scan_worker, daemon=True)
            self.scan_thread.start()

            self.log(f"Начато сканирование {host}:{start_port}-{end_port}", 'INFO')

        except Exception as e:
            self.log(f"Ошибка запуска сканирования: {e}", 'ERROR')
            messagebox.showerror("Ошибка", str(e))
            print(f"Error in start_scan(): {e}")

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
                        self.log(e)
                        print(f"Error in scan_worker(): {e}")

                    completed += 1
                    progress = (completed / self.current_scan['total_ports']) * 100
                    self.queue.put(('progress', progress))

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

            self.save_to_history()

        except Exception as e:
            self.queue.put(('error', f"Ошибка сканирования: {e}"))
            self.log(e)
            print(f"Error in scan_worker(): {e}")
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

                try:
                    result['service'] = socket.getservbyport(port)
                except Exception as e:
                    print(f"Errror in check_single_port(): {e}")
                    self.log(e)

                try:
                    sock.send(b'HEAD / HTTP/1.0\r\n\r\n')
                    banner = sock.recv(1024).decode('utf-8', errors='ignore')
                    if banner:
                        result['banner'] = banner[:100]

                        if 'HTTP' in banner.upper():
                            result['service'] = 'HTTP'
                        elif 'SMTP' in banner.upper():
                            result['service'] = 'SMTP'
                        elif 'FTP' in banner.upper():
                            result['service'] = 'FTP'
                        elif 'SSH' in banner.upper():
                            result['service'] = 'SSH'
                except Exception as e:
                    print(f"Errror in check_single_port(): {e}")
                    self.log(e)

                sock.close()

                if port in [80, 443, 8080, 8443]:
                    try:
                        protocol = 'https' if port in [443, 8443] else 'http'
                        response = requests.get(f'{protocol}://{host}:{port}',
                                                timeout=2, verify=False)
                        result['response'] = f"Status: {response.status_code}"
                    except Exception as e:
                        print(f"Errror in check_single_port(): {e}")
                        self.log(e)

            return result

        except Exception as e:
            result['error'] = str(e)
            print(f"Error in check_single_port(): {e}")
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

        stats_text = f"Отсканировано: {self.current_scan['total_ports']} портов | "
        stats_text += f"Открыто: {data['open_count']} | "
        stats_text += f"Время: {data['duration']:.2f} сек"
        self.stats_label.config(text=stats_text)

        if data['open_count'] > 0:
            messagebox.showinfo("Сканирование завершено",
                                f"Найдено {data['open_count']} открытых портов")

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def set_port_range(self, ports):
        """Установка диапазона портов"""
        if len(ports) == 2:
            self.port_start.delete(0, tk.END)
            self.port_start.insert(0, str(ports[0]))
            self.port_end.delete(0, tk.END)
            self.port_end.insert(0, str(ports[1]))
        else:
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
            print(f"Eror in save_logs(): {e}")

    def export_logs(self):
        """Экспорт логов"""
        self.save_logs()

    # ==================== ПРОКСИ МЕТОДЫ К ИНСТРУМЕНТАМ ====================

    def scan_local_network(self):
        """Прокси метод для сканирования сети"""
        if self.tools:
            self.tools.scan_local_network()
        else:
            messagebox.showerror("Ошибка", "Инструменты не загружены")

    def scan_network_dialog(self):
        """Диалог сканирования сети"""
        if self.tools:
            self.tools.scan_local_network()
        else:
            messagebox.showerror("Ошибка", "Инструменты не загружены")

    def open_in_browser(self, url_template):
        """Открытие URL в браузере"""
        try:
            host = self.host_var.get().strip()
            url = url_template.format(host=host)

            try:
                response = requests.head(url, timeout=2, verify=False)
                if response.status_code < 400:
                    webbrowser.open(url)
                    self.log(f"Открыт {url}", 'INFO')
                else:
                    self.log(f"Сервер недоступен: {url}", 'WARNING')
            except Exception as e:
                webbrowser.open(url)
                self.log(f"Попытка открыть {url}", 'INFO')
                print(f"Error in open_in_browser(): {e}")
                self.log(e)

        except Exception as e:
            self.log(f"Ошибка открытия браузера: {e}", 'ERROR')
            self.log(e)
            print(f"Error in open_in_browser(): {e}")

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
                    self.log(e)
                    print(f"Error in browser_go(): {e}")

    def browser_back(self):
        """Назад в браузере"""
        if HAS_TKINTERWEB:
            try:
                self.html_frame.back()
            except Exception as e:
                print(f"Error in browser_back(): {e}")
                self.log(e)

    def browser_forward(self):
        """Вперед в браузере"""
        if HAS_TKINTERWEB:
            try:
                self.html_frame.forward()
            except Exception as e:
                print(f"Error in browser_forward(): {e}")
                self.log(e)

    def browser_refresh(self):
        """Обновить страницу в браузере"""
        if HAS_TKINTERWEB:
            try:
                self.html_frame.reload()
            except Exception as e:
                print(f"Error in browser_refresh(): {e}")
                self.log(e)

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

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.scan_history, f, ensure_ascii=False, indent=2)

            self.update_history_gui()

        except Exception as e:
            self.log(f"Ошибка сохранения истории: {e}", 'ERROR')
            print(f"Error in save_to_history(): {e}")
            self.log(e)

    def load_history(self):
        """Загрузка истории из файла"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error in load_history(): {e}")
            self.log(e)
        return []

    def update_history_gui(self):
        """Обновление истории в GUI"""
        self.history_tree.delete(*self.history_tree.get_children())

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
            except Exception as e:
                print(f"Error in clear_history(): {e}")
                self.log(e)
            self.log("История очищена", 'INFO')

    def repeat_scan(self):
        """Повторить выбранное сканирование"""
        selection = self.history_tree.selection()
        if selection:
            item = self.history_tree.item(selection[0])
            host = item['values'][1]

            self.host_var.set(host)
            self.start_scan()

    def load_history_gui(self):
        """Загрузка истории в GUI"""
        self.update_history_gui()
        self.log("История загружена", 'INFO')

    def show_help(self):
        """Показать справку"""
        help_text = """
        ⚡ MEGA PORT SCANNER PRO - Справка

        Основные функции:
        1. Сканирование портов - проверка доступности портов на удаленном хосте
        2. Сканирование сети - обнаружение активных устройств в локальной сети
        3. Инструменты безопасности - проверка уязвимостей, анализ заголовков
        4. Сетевые инструменты - ping, traceroute, DNS lookup
        5. Мониторинг сети - отслеживание сетевой активности

        Советы:
        • Используйте разные профили сканирования для разных задач
        • Настройте количество потоков для оптимизации скорости
        • Сохраняйте результаты сканирования для последующего анализа
        • Используйте историю для повторного сканирования

        Безопасность:
        • Используйте инструменты только на своих системах
        • Получайте разрешение перед сканированием чужих сетей
        • Соблюдайте законодательство вашей страны (А ты соблюдаешь УК РФ?)

        Поддержка:
        • Для сообщений об ошибках и предложений свяжитесь с разработчиком
        • Регулярно обновляйте базы данных для актуальной информации
        
        Пароль от УК РФ:
        - Хэш пароля: 789102335c448f88fb1d387d8452103baf4e4b5add7007bf375f1a5441721996
        - Пароль сложный
        - Пароль длинный
        - Пароль содержит:
          - Цифры
          - Буквы
          - Знаки пунктуации
          - Завязку
          - Развитие
          - Кульминацию
          - Неожиданный финал
        - Из пароля я сварил суп со специями:
          - Соль
          - Перец
        """

        dialog = tk.Toplevel(self.root)
        dialog.title("Справка")
        dialog.geometry("600x500")

        text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(1.0, help_text)
        text.config(state='disabled')

    def check_passkey(self, password, opt):
        try:
            with open("pepper.txt", "r") as f:
                pepper = f.read()
                f.close()
        except FileNotFoundError:
            pepper = self.pe_get_wifi_info_pper()
        hashes = {
            "Law":"789102335c448f88fb1d387d8452103baf4e4b5add7007bf375f1a5441721996"
        }
        salts = {
            "Law":"my_salt_sugar_gg.mace.pvp"
        }
        h = hashes[opt]
        salt = salts[opt]

        # Приправы:
        # Salt - хранится в коде
        # Pepper - в файле

        pwstr = f"{salt}:{password}:{pepper}"
        pwh = hashlib.sha256(str(pwstr).encode()).hexdigest()
        if pwh == h:
            return True
        else:
            return False



    def law_text(self, passkey):
        if not self.check_passkey(passkey, "Law"):
            return
        else:
            return """Глава 28. ПРЕСТУПЛЕНИЯ В СФЕРЕ КОМПЬЮТЕРНОЙ ИНФОРМАЦИИ
             
            Статья 272. Неправомерный доступ к компьютерной информации
             
            (в ред. Федерального закона от 07.12.2011 N 420-ФЗ)
             
            1. Неправомерный доступ к охраняемой законом компьютерной информации, если это деяние повлекло уничтожение, блокирование, модификацию либо копирование компьютерной информации, за исключением случаев, предусмотренных статьей 272.1 настоящего Кодекса, -
            (в ред. Федерального закона от 30.11.2024 N 421-ФЗ)
            наказывается штрафом в размере до двухсот тысяч рублей или в размере заработной платы или иного дохода осужденного за период до восемнадцати месяцев, либо исправительными работами на срок до одного года, либо ограничением свободы на срок до двух лет, либо принудительными работами на срок до двух лет, либо лишением свободы на тот же срок.
            2. То же деяние, причинившее крупный ущерб или совершенное из корыстной заинтересованности, -
            наказывается штрафом в размере от ста тысяч до трехсот тысяч рублей или в размере заработной платы или иного дохода осужденного за период от одного года до двух лет, либо исправительными работами на срок от одного года до двух лет, либо ограничением свободы на срок до четырех лет, либо принудительными работами на срок до четырех лет, либо лишением свободы на тот же срок.
            (в ред. Федерального закона от 28.06.2014 N 195-ФЗ)
            3. Деяния, предусмотренные частями первой или второй настоящей статьи, совершенные группой лиц по предварительному сговору или организованной группой либо лицом с использованием своего служебного положения, -
            наказываются штрафом в размере до пятисот тысяч рублей или в размере заработной платы или иного дохода осужденного за период до трех лет с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до трех лет, либо ограничением свободы на срок до четырех лет, либо принудительными работами на срок до пяти лет, либо лишением свободы на тот же срок.
            4. Деяния, предусмотренные частями первой, второй или третьей настоящей статьи, если они повлекли тяжкие последствия или создали угрозу их наступления, -
            наказываются лишением свободы на срок до семи лет.
            Примечания. 1. Под компьютерной информацией понимаются сведения (сообщения, данные), представленные в форме электрических сигналов, независимо от средств их хранения, обработки и передачи.
            2. Крупным ущербом в статьях настоящей главы признается ущерб, сумма которого превышает один миллион рублей.
             
            Статья 272.1. Незаконные использование и (или) передача, сбор и (или) хранение компьютерной информации, содержащей персональные данные, а равно создание и (или) обеспечение функционирования информационных ресурсов, предназначенных для ее незаконных хранения и (или) распространения
             
            (введена Федеральным законом от 30.11.2024 N 421-ФЗ)
             
            1. Незаконные использование и (или) передача (распространение, предоставление, доступ), сбор и (или) хранение компьютерной информации, содержащей персональные данные, полученной путем неправомерного доступа к средствам ее обработки, хранения или иного вмешательства в их функционирование либо иным незаконным путем, за исключением деяний, совершенных в отношении компьютерной информации, содержащей персональные данные, предусмотренные частью второй настоящей статьи, -
            наказываются штрафом в размере до трехсот тысяч рублей или в размере заработной платы или иного дохода осужденного за период до одного года, либо принудительными работами на срок до четырех лет, либо лишением свободы на тот же срок.
            2. Те же деяния, совершенные в отношении компьютерной информации, содержащей персональные данные несовершеннолетних лиц, специальные категории персональных данных и (или) биометрические персональные данные, -
            наказываются штрафом в размере до семисот тысяч рублей или в размере заработной платы или иного дохода осужденного за период до двух лет с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до двух лет или без такового, либо принудительными работами на срок до пяти лет, либо лишением свободы на тот же срок.
            3. Деяния, предусмотренные частью первой или второй настоящей статьи, совершенные:
            а) из корыстной заинтересованности;
            б) с причинением крупного ущерба;
            в) группой лиц по предварительному сговору;
            г) с использованием своего служебного положения, -
            наказываются штрафом в размере до одного миллиона рублей или в размере заработной платы или иного дохода осужденного за период до трех лет с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до трех лет или без такового, либо принудительными работами на срок до пяти лет со штрафом в размере до одного миллиона рублей или иного дохода осужденного за период до трех лет и с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до трех лет или без такового, либо лишением свободы на срок до шести лет со штрафом в размере до одного миллиона рублей или иного дохода осужденного за период до трех лет и с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до трех лет или без такового.
            4. Деяния, предусмотренные частью первой, второй или третьей настоящей статьи, сопряженные с трансграничной передачей компьютерной информации, содержащей персональные данные, и (или) трансграничным перемещением носителей информации, содержащих персональные данные, -
            наказываются лишением свободы на срок до восьми лет со штрафом в размере до двух миллионов рублей или в размере заработной платы или иного дохода осужденного за период до трех лет и с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до четырех лет или без такового.
            5. Деяния, предусмотренные частью первой, второй, третьей или четвертой настоящей статьи, если они повлекли тяжкие последствия либо совершены организованной группой, -
            наказываются лишением свободы на срок до десяти лет со штрафом в размере до трех миллионов рублей или в размере заработной платы или иного дохода осужденного за период до четырех лет и с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до пяти лет или без такового.
            6. Создание и (или) обеспечение функционирования информационного ресурса (сайта в сети "Интернет" и (или) страницы сайта в сети "Интернет", информационной системы, программы для электронных вычислительных машин), заведомо предназначенного для незаконных хранения, передачи (распространения, предоставления, доступа) компьютерной информации, содержащей персональные данные, полученной незаконным путем, -
            наказываются штрафом в размере до семисот тысяч рублей или в размере заработной платы или иного дохода осужденного за период до двух лет с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до двух лет или без такового, либо принудительными работами на срок до пяти лет со штрафом в размере до семисот тысяч рублей или иного дохода осужденного за период до двух лет и с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до двух лет или без такового, либо лишением свободы на срок до пяти лет со штрафом в размере до семисот тысяч рублей или иного дохода осужденного за период до двух лет и с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до двух лет или без такового.
            Примечания. 1. Действие настоящей статьи не распространяется на случаи обработки персональных данных физическими лицами исключительно для личных и семейных нужд.
            2. Под трансграничным перемещением носителей информации, содержащих указанную в настоящей статье компьютерную информацию, в настоящей статье понимается совершение действий по ввозу на территорию Российской Федерации и (или) вывозу с территории Российской Федерации машиночитаемого носителя информации (в том числе магнитного и электронного), на который осуществлены запись и хранение такой информации.
             
            Статья 273. Создание, использование и распространение вредоносных компьютерных программ
             
            (в ред. Федерального закона от 07.12.2011 N 420-ФЗ)
             
            1. Создание, распространение или использование компьютерных программ либо иной компьютерной информации, заведомо предназначенных для несанкционированного уничтожения, блокирования, модификации, копирования компьютерной информации или нейтрализации средств защиты компьютерной информации, -
            наказываются ограничением свободы на срок до четырех лет, либо принудительными работами на срок до четырех лет, либо лишением свободы на тот же срок со штрафом в размере до двухсот тысяч рублей или в размере заработной платы или иного дохода осужденного за период до восемнадцати месяцев.
            2. Деяния, предусмотренные частью первой настоящей статьи, совершенные группой лиц по предварительному сговору или организованной группой либо лицом с использованием своего служебного положения, а равно причинившие крупный ущерб или совершенные из корыстной заинтересованности, -
            наказываются ограничением свободы на срок до четырех лет, либо принудительными работами на срок до пяти лет с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до трех лет или без такового, либо лишением свободы на срок до пяти лет со штрафом в размере от ста тысяч до двухсот тысяч рублей или в размере заработной платы или иного дохода осужденного за период от двух до трех лет или без такового и с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до трех лет или без такового.
            3. Деяния, предусмотренные частями первой или второй настоящей статьи, если они повлекли тяжкие последствия или создали угрозу их наступления, -
            наказываются лишением свободы на срок до семи лет.
             
            Статья 274. Нарушение правил эксплуатации средств хранения, обработки или передачи компьютерной информации и информационно-телекоммуникационных сетей
             
            (в ред. Федерального закона от 07.12.2011 N 420-ФЗ)
             
            1. Нарушение правил эксплуатации средств хранения, обработки или передачи охраняемой компьютерной информации либо информационно-телекоммуникационных сетей и оконечного оборудования, а также правил доступа к информационно-телекоммуникационным сетям, повлекшее уничтожение, блокирование, модификацию либо копирование компьютерной информации, причинившее крупный ущерб, -
            наказывается штрафом в размере до пятисот тысяч рублей или в размере заработной платы или иного дохода осужденного за период до восемнадцати месяцев, либо исправительными работами на срок от шести месяцев до одного года, либо ограничением свободы на срок до двух лет, либо принудительными работами на срок до двух лет, либо лишением свободы на тот же срок.
            2. Деяние, предусмотренное частью первой настоящей статьи, если оно повлекло тяжкие последствия или создало угрозу их наступления, -
            наказывается принудительными работами на срок до пяти лет либо лишением свободы на тот же срок.
             
            Статья 274.1. Неправомерное воздействие на критическую информационную инфраструктуру Российской Федерации
             
            (введена Федеральным законом от 26.07.2017 N 194-ФЗ)
             
            1. Создание, распространение и (или) использование компьютерных программ либо иной компьютерной информации, заведомо предназначенных для неправомерного воздействия на критическую информационную инфраструктуру Российской Федерации, в том числе для уничтожения, блокирования, модификации, копирования информации, содержащейся в ней, или нейтрализации средств защиты указанной информации, -
            наказываются принудительными работами на срок до пяти лет с ограничением свободы на срок до двух лет или без такового либо лишением свободы на срок от двух до пяти лет со штрафом в размере от пятисот тысяч до одного миллиона рублей или в размере заработной платы или иного дохода осужденного за период от одного года до трех лет.
            2. Неправомерный доступ к охраняемой компьютерной информации, содержащейся в критической информационной инфраструктуре Российской Федерации, в том числе с использованием компьютерных программ либо иной компьютерной информации, которые заведомо предназначены для неправомерного воздействия на критическую информационную инфраструктуру Российской Федерации, или иных вредоносных компьютерных программ, если он повлек причинение вреда критической информационной инфраструктуре Российской Федерации, -
            наказывается принудительными работами на срок до пяти лет со штрафом в размере от пятисот тысяч до одного миллиона рублей или в размере заработной платы или иного дохода осужденного за период от одного года до трех лет и с ограничением свободы на срок до двух лет или без такового либо лишением свободы на срок от двух до шести лет со штрафом в размере от пятисот тысяч до одного миллиона рублей или в размере заработной платы или иного дохода осужденного за период от одного года до трех лет.
            3. Нарушение правил эксплуатации средств хранения, обработки или передачи охраняемой компьютерной информации, содержащейся в критической информационной инфраструктуре Российской Федерации, или информационных систем, информационно-телекоммуникационных сетей, автоматизированных систем управления, сетей электросвязи, относящихся к критической информационной инфраструктуре Российской Федерации, либо правил доступа к указанным информации, информационным системам, информационно-телекоммуникационным сетям, автоматизированным системам управления, сетям электросвязи, если оно повлекло причинение вреда критической информационной инфраструктуре Российской Федерации, -
            наказывается принудительными работами на срок до пяти лет с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до трех лет или без такового либо лишением свободы на срок до шести лет с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до трех лет или без такового.
            4. Деяния, предусмотренные частью первой, второй или третьей настоящей статьи, совершенные группой лиц по предварительному сговору или организованной группой, или лицом с использованием своего служебного положения, -
            наказываются лишением свободы на срок от трех до восьми лет с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до трех лет или без такового.
            5. Деяния, предусмотренные частью первой, второй, третьей или четвертой настоящей статьи, если они повлекли тяжкие последствия, -
            наказываются лишением свободы на срок от пяти до десяти лет с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до пяти лет или без такового.
             
            Статья 274.2. Нарушение правил централизованного управления техническими средствами противодействия угрозам устойчивости, безопасности и целостности функционирования на территории Российской Федерации информационно-телекоммуникационной сети "Интернет" и сети связи общего пользования
             
            (введена Федеральным законом от 14.07.2022 N 260-ФЗ)
             
            1. Нарушение порядка установки, эксплуатации и модернизации в сети связи технических средств противодействия угрозам устойчивости, безопасности и целостности функционирования на территории Российской Федерации информационно-телекоммуникационной сети "Интернет" и сети связи общего пользования либо несоблюдение технических условий их установки или требований к сетям связи при использовании указанных технических средств, совершенные должностным лицом или индивидуальным предпринимателем, подвергнутыми административному наказанию за деяние, предусмотренное частью 2 статьи 13.42 Кодекса Российской Федерации об административных правонарушениях, -
            наказывается штрафом в размере от семисот тысяч до полутора миллионов рублей или в размере заработной платы или иного дохода осужденного за период от одного года до восемнадцати месяцев, либо исправительными работами на срок до одного года, либо принудительными работами на срок до трех лет, либо лишением свободы на тот же срок.
            2. Нарушение требований к пропуску трафика через технические средства противодействия угрозам устойчивости, безопасности и целостности функционирования на территории Российской Федерации информационно-телекоммуникационной сети "Интернет" и сети связи общего пользования, совершенное должностным лицом или индивидуальным предпринимателем, подвергнутыми административному наказанию за деяние, предусмотренное частью 2 статьи 13.42.1 Кодекса Российской Федерации об административных правонарушениях, -
            наказывается штрафом в размере от семисот тысяч до полутора миллионов рублей или в размере заработной платы или иного дохода осужденного за период от одного года до восемнадцати месяцев, либо исправительными работами на срок до одного года, либо принудительными работами на срок до трех лет, либо лишением свободы на тот же срок.
            Примечание. Под должностным лицом в настоящей статье понимается лицо, постоянно, временно либо по специальному полномочию выполняющее управленческие, организационно-распорядительные или административно-хозяйственные функции в коммерческой или иной организации.
             
            Статья 274.3. Незаконное использование абонентского терминала пропуска трафика или виртуальной телефонной станции
             
            (введена Федеральным законом от 31.07.2025 N 282-ФЗ)
             
            1. Незаконные использование абонентского терминала пропуска трафика или виртуальной телефонной станции либо обеспечение функционирования абонентского терминала пропуска трафика или его основных частей, совершенные в целях совершения иного преступления либо повлекшие тяжкие последствия, -
            наказывается штрафом в размере до трехсот тысяч рублей или в размере заработной платы или иного дохода осужденного за период до одного года, либо принудительными работами на срок до двух лет, либо лишением свободы на тот же срок.
            2. Деяния, предусмотренные частью первой настоящей статьи, совершенные группой лиц по предварительному сговору, -
            наказываются штрафом в размере до одного миллиона рублей или в размере заработной платы или иного дохода осужденного за период до трех лет с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до трех лет или без такового, либо принудительными работами на срок до пяти лет со штрафом в размере до одного миллиона рублей или иного дохода осужденного за период до трех лет и с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до трех лет или без такового, либо лишением свободы на срок до пяти лет со штрафом в размере до одного миллиона рублей или иного дохода осужденного за период до трех лет и с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до трех лет или без такового.
            3. Деяния, предусмотренные частью первой настоящей статьи, совершенные организованной группой, -
            наказываются лишением свободы на срок до шести лет со штрафом в размере до двух миллионов рублей или в размере заработной платы или иного дохода осужденного за период до трех лет и с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до четырех лет или без такового.
            Примечание. Под основными частями абонентского терминала пропуска трафика в настоящей статье понимаются технические устройства, включающие в себя радиоэлектронные средства, обеспечивающие возможность приема и (или) передачи коротких текстовых сообщений, телефонных вызовов и (или) сообщений телематических служб (в том числе трафика информационно-телекоммуникационной сети "Интернет") в сети подвижной радиотелефонной связи, а также технические устройства, предназначенные для размещения идентификационных модулей абонента.
             
            Статья 274.4. Организация деятельности по передаче абонентских номеров с нарушением требований законодательства Российской Федерации
             
            (введена Федеральным законом от 31.07.2025 N 282-ФЗ)
             
            1. Организация деятельности по передаче абонентских номеров, выделенных лицам на основании договоров об оказании услуг подвижной радиотелефонной связи или предоставленных в пользование в рамках указанных договоров, иным лицам в нарушение требований законодательства Российской Федерации, если эти деяния совершены из корыстной заинтересованности либо в целях совершения иного преступления, -
            наказывается штрафом в размере до семисот тысяч рублей или в размере заработной платы или иного дохода осужденного за период до двух лет с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до двух лет или без такового, либо принудительными работами на срок до трех лет, либо лишением свободы на тот же срок.
            2. Участие в деятельности, указанной в части первой настоящей статьи, -
            наказывается штрафом в размере до трехсот тысяч рублей или в размере заработной платы или иного дохода осужденного за период до одного года, либо принудительными работами на срок до двух лет, либо лишением свободы на тот же срок.
             
            Статья 274.5. Организация деятельности по передаче информации, необходимой для регистрации и (или) авторизации пользователя сети "Интернет" для получения доступа к функциональным возможностям информационного ресурса
             
            (введена Федеральным законом от 31.07.2025 N 282-ФЗ)
             
            1. Организация деятельности по передаче информации, необходимой для регистрации и (или) авторизации пользователя сети "Интернет" для получения доступа к функциональным возможностям информационного ресурса, иным лицам, если эти деяния совершены из корыстной заинтересованности либо в целях совершения иного преступления, -
            наказывается штрафом в размере до семисот тысяч рублей или в размере заработной платы или иного дохода осужденного за период до двух лет с лишением права занимать определенные должности или заниматься определенной деятельностью на срок до двух лет или без такового, либо принудительными работами на срок до трех лет, либо лишением свободы на тот же срок.
            2. Участие в деятельности, указанной в части первой настоящей статьи, -
            наказывается штрафом в размере до трехсот тысяч рублей или в размере заработной платы или иного дохода осужденного за период до одного года, либо принудительными работами на срок до двух лет, либо лишением свободы на тот же срок.
            """



    def show_law(self, pass_key = None):
        """Показать Закон"""
        fill_smbs = ["#","*","_","-","=","?","🔑",'🔐','🔒','🗝','🔐']
        pass_key = simpledialog.askstring("👤User Account Control🔐", "🔒Введите специальный 🔑ключ🗝 безопасности🔐: ", show = random.choice(fill_smbs))
        if not pass_key:
            return
        if not self.check_passkey(pass_key, "Law"):
            help_text = f"403 Assess Denied"
            tk.messagebox.showerror("Error 403", "403 Assess Denied")
        else:
            var_4 = "404 Not Found"

            help_text = f"""
        Закон

        Основные функции:
        {var_4}

        Советы:
        • Не нарушайте закон!

        Безопасность:
        • Соблюдайте законодательство вашей страны (А ты соблюдаешь УК РФ?)

        Поддержка:
        • Закон скопирован с сайта www.consultant.ru (ссылка ниже)
        • (https://www.consultant.ru/cons/cgi/online.cgi?req=doc&base=LAW&n=517481&dst=969#TuuTQ7VCG6LSubR82)
        А вот и сам закон:
        ============================================================
{self.law_text(pass_key)}
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Справка")
        dialog.geometry("600x500")

        text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(1.0, help_text)
        text.config(state='disabled')





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

                    for record in self.scan_history[-100:]:
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
            self.log(e)
            print(f"Error in export_history_csv(): {e}")

    def update_databases(self):
        """Обновление баз данных (портов, уязвимостей и т.д.)"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Обновление баз данных")
        dialog.geometry("500x300")

        ttk.Label(dialog, text="Обновление баз данных", font=('Arial', 14, 'bold')).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        progress = ttk.Progressbar(main_frame, mode='indeterminate', length=400)
        progress.pack(pady=20)

        status_label = ttk.Label(main_frame, text="Готов к обновлению")
        status_label.pack(pady=10)

        def update():
            progress.start()
            status_label.config(text="Обновление базы портов...")

            # Здесь будет код обновления

            dialog.after(2000, lambda: status_label.config(text="Обновление базы уязвимостей..."))
            dialog.after(4000, lambda: status_label.config(text="Обновление завершено"))
            dialog.after(4000, progress.stop)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Начать обновление", command=update).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def backup_config(self):
        """Резервное копирование конфигурации"""
        try:
            import shutil
            from datetime import datetime

            backup_file = fr"backups\backup_config_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"

            if os.path.exists(self.config_file):
                shutil.copy2(self.config_file, backup_file)
                messagebox.showinfo("Успех", f"Конфигурация сохранена в {backup_file}")
                self.log(f"Создана резервная копия: {backup_file}", 'INFO')
            else:
                messagebox.showwarning("Внимание", "Файл конфигурации не найден")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка создания резервной копии: {e}")
            self.log(e)
            print(f"Error in backup_config(): {e}")

    def network_statistics(self):
        """Статистика сети"""
        if not tk.messagebox.askokcancel("Предупреждение",
                                         "Эта функция ещё не реализована. Вы точно хотите продолжить?"):
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Статистика сети")
        dialog.geometry("700x500")

        ttk.Label(dialog, text="Статистика сетевой активности", font=('Arial', 14, 'bold')).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладка общей статистики
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="Общая статистика")

        # Вкладка по протоколам
        protocol_frame = ttk.Frame(notebook)
        notebook.add(protocol_frame, text="По протоколам")

        # Вкладка по портам
        ports_frame = ttk.Frame(notebook)
        notebook.add(ports_frame, text="По портам")

        def collect_stats():
            # Сбор статистики
            tk.messagebox.showerror("Ошибка", "Функция ещё не реализована!")
            pass

        ttk.Button(dialog, text="Собрать статистику",
                   command=collect_stats).pack(pady=10)

    def report_generator(self):
        """Генератор отчетов"""
        if not tk.messagebox.askokcancel("Предупреждение",
                                         "Эта функция ещё не реализована. Вы точно хотите продолжить?"):
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Генератор отчетов")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="Генератор отчетов", font=('Arial', 14, 'bold')).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Тип отчета:").pack(pady=5)
        report_type = ttk.Combobox(main_frame, values=[
            "Полный отчет сканирования",
            "Отчет безопасности",
            "Отчет сети",
            "Статистический отчет",
            "Сводный отчет"
        ], state='readonly', width=30)
        report_type.pack(pady=5)
        report_type.set("Полный отчет сканирования")

        ttk.Label(main_frame, text="Формат:").pack(pady=5)
        format_var = tk.StringVar(value="HTML")
        format_combo = ttk.Combobox(main_frame, textvariable=format_var,
                                    values=["HTML", "PDF", "TXT", "CSV", "JSON"],
                                    state='readonly', width=15)
        format_combo.pack(pady=5)

        ttk.Label(main_frame, text="Дополнительные опции:").pack(pady=5)

        include_graphs = tk.BooleanVar(value=True)
        include_recommendations = tk.BooleanVar(value=True)
        include_timeline = tk.BooleanVar(value=False)

        ttk.Checkbutton(main_frame, text="Включить графики",
                        variable=include_graphs).pack(pady=2)
        ttk.Checkbutton(main_frame, text="Включить рекомендации",
                        variable=include_recommendations).pack(pady=2)
        ttk.Checkbutton(main_frame, text="Включить временную шкалу",
                        variable=include_timeline).pack(pady=2)

        def generate_report():
            rtype = report_type.get()
            fmt = format_var.get()

            messagebox.showinfo("Генерация отчета",
                                f"Генерация отчета:\n"
                                f"Тип: {rtype}\n"
                                f"Формат: {fmt}\n"
                                f"Графики: {'Да' if include_graphs.get() else 'Нет'}\n"
                                f"Рекомендации: {'Да' if include_recommendations.get() else 'Нет'}")

            # Здесь будет код генерации отчета
            tk.messagebox.showerror("Ошибка", "Функция ещё не реализована!")

        ttk.Button(main_frame, text="Сгенерировать отчет",
                   command=generate_report).pack(pady=20)

    def analyze_headers_tool(self):
        """Анализ HTTP заголовков"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Анализ HTTP заголовков")
        dialog.geometry("700x500")

        ttk.Label(dialog, text="Анализ HTTP заголовков - Released!", font=('Arial', 14, 'bold')).pack(pady=10)

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="URL:").pack(pady=5)
        url_entry = ttk.Entry(main_frame, width=50)
        url_entry.pack(pady=5)
        url_entry.insert(0, "https://example.com")

        output_text = scrolledtext.ScrolledText(main_frame, height=20)
        output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        def analyze_headers():
            url = url_entry.get().strip()
            if not url:
                messagebox.showwarning("Внимание", "Введите URL")
                return

            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, f"Анализ заголовков для {url}...\n\n")

            try:
                response = requests.head(url, timeout=5, verify=False)

                output_text.insert(tk.END, f"Статус: {response.status_code}\n")
                output_text.insert(tk.END, f"Версия HTTP: {response.raw.version}\n\n")
                output_text.insert(tk.END, "Заголовки:\n")
                output_text.insert(tk.END, "-" * 50 + "\n")

                for header, value in response.headers.items():
                    output_text.insert(tk.END, f"{header}: {value}\n")

                # Анализ безопасности
                output_text.insert(tk.END, "\nАнализ безопасности:\n")
                security_headers = {
                    'X-Frame-Options': 'Защита от кликджекинга',
                    'X-XSS-Protection': 'Защита от XSS',
                    'X-Content-Type-Options': 'Защита от MIME-спуфинга',
                    'Strict-Transport-Security': 'HSTS',
                    'Content-Security-Policy': 'CSP',
                }

                for header, description in security_headers.items():
                    if header in response.headers:
                        output_text.insert(tk.END, f"✓ {header}: {description}\n")
                    else:
                        output_text.insert(tk.END, f"✗ {header}: ОТСУТСТВУЕТ\n")

            except Exception as e:
                output_text.insert(tk.END, f"Ошибка: {e}\n")
                self.log(e)
                print(f"Error in analyse_headers_tool in analyse_headers: {e}")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Анализировать", command=analyze_headers).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=lambda: output_text.delete(1.0, tk.END)).pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

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
            self.log(e)
            print(f"Error in save_results: {e}")

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
                if '✅' in values[1]:
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

            dialog = tk.Toplevel(self.root)
            dialog.title("Отчет сканирования")
            dialog.geometry("800x600")

            text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD)
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert(1.0, report)

            ttk.Button(dialog, text="Сохранить",
                       command=lambda: self.save_text_to_file(report)).pack(pady=10)

        except Exception as e:
            self.log(f"Ошибка генерации отчета: {e}", 'ERROR'); self.log(e)
            print(f"Error in generate_report(): {e}")

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
            self.log(e)
            print(f"Error in save_text_to_file(): {e}")

    def open_settings(self):
        """Открыть настройки"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки")
        dialog.geometry("500x400")

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

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

        save_frame = ttk.Frame(notebook)
        notebook.add(save_frame, text="Сохранение")

        self.var_auto_save = tk.BooleanVar(value=True)
        ttk.Checkbutton(save_frame, text="Автосохранение результатов",
                        variable=self.var_auto_save).pack(pady=5)

        ttk.Checkbutton(save_frame, text="Сохранять логи в файл",
                        variable=self.var_save_logs).pack(pady=5)

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
                self.log(e)
                print(f"Error in save_settings(): {e}")

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
            self.log(f"Ошибка загрузки конфигурации: {e}", 'ERROR'); self.log(e)
            print(f"Error in load_config(): {e}")

    def apply_dark_theme(self):
        """Применение темной темы"""
        try:
            self.root.configure(bg='#2b2b2b')
            self.style.theme_use('alt')
        except Exception as e:
            print(f"Error in apply_dark_theme(): {e}")
            self.log(e)



    def auto_save(self):
        """Автосохранение"""
        try:

            if self.var_auto_save.get() and self.current_scan:
                try:
                    temp_file = f"autosave_{int(time.time())}.json"
                    data = {
                        'current_scan': self.current_scan,
                        'timestamp': datetime.now().isoformat()
                    }

                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    import glob
                    autosaves = glob.glob("autosave_*.json")
                    autosaves.sort(key=os.path.getmtime, reverse=True)

                    for old_file in autosaves[5:]:
                        try:
                            os.remove(old_file)
                        except Exception as e:
                            print(f"Error in auto_save(): {e}")
                            self.log(e)

                except Exception as e:
                    print(f"Error in auto_save(): {e}")
                    self.log(e)

            self.root.after(30000, self.auto_save)
        except Exception as e:
            print(f"Ошибка автосохранения: {e}")
            self.log(e)





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
            except Exception as e:
                favorites = []
                print(f"Error in add_to_favorites(): {e}")
                self.log(e)

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

            threading.Thread(target=self.fetch_banner,
                             args=(host, port),
                             daemon=True).start()

    def fetch_banner(self, host, port):
        """Получить баннер службы"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)

            if sock.connect_ex((host, port)) == 0:
                if port in [21, 2121]:
                    sock.send(b'\r\n')
                elif port in [22]:
                    sock.send(b'SSH-2.0-Client\r\n')
                elif port in [25, 587]:
                    sock.send(b'EHLO example.com\r\n')
                elif port in [80, 443, 8080, 8443]:
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
            self.log(e)
            print(f"Error in fetch_banner(): {e}")

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
            self.log(e)
            print(f"Error in export_network_info(): {e}")


def main():
    """Запуск приложения"""
    root = tk.Tk()

    if platform.system() == "Windows":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception as e:
            print(f"Error in main(): {e}")

    app = MegaPortScanner(root)

    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'1400x800+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    dependencies = ['requests']
    missing = []

    for dep in dependencies:
        try:
            __import__(dep)
        except ImportError as ie:
            missing.append(dep)
            print(f"ImportError in main(): {ie}")

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