"""
Wi-Fi Scanner Module
Полнофункциональный сканер Wi-Fi сетей для Windows/Linux
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import re
import json
from datetime import datetime
import platform
import threading
import queue
import time
from collections import defaultdict
import os
import sys
from typing import List, Dict, Optional, Any
import csv



class WiFiScanner:
    """Класс для сканирования и анализа Wi-Fi сетей"""

    def __init__(self, parent=None):
        """Инициализация сканера Wi-Fi"""
        self.parent = parent
        self.scanning = False
        self.current_wifi_networks = []
        self.selected_network = None
        self.wifi_tree = None
        self.wifi_details = None
        self.status_label = None
        self.networks_count_label = None
        self.scan_interval = "10"
        self.auto_scan_var = False
        self.gui_queue = queue.Queue()  # Очередь для сообщений между потоками


        # MAC-адреса производителей (сокращенный список)
        self.vendor_db = {
            '001C10': 'Cisco', '000C29': 'VMware', '001B21': 'Netgear',
            '001A2B': 'ASUS', '001D0F': 'Buffalo', '001E8C': 'D-Link',
            '001FC6': 'EE', '0021E9': 'TP-Link', '0022CF': 'ZyXEL',
            '0023CD': 'Apple', '0024FE': 'Huawei', '0026CE': 'LG',
            '002710': 'Microsoft', '002764': 'Xiaomi', '080028': 'Intel',
            '000B6A': 'Samsung', '0001C8': 'HTC', '000F8F': 'Motorola',
            '0010FA': 'Nokia', '00156D': 'Sony', '001C62': 'ZTE',
            '001E74': 'Belkin', '002293': 'Linksys', '00236C': 'Tenda',
            '0050F2': 'D-Link', '0090D0': 'D-Link', '080069': 'Intel',
            '08005A': 'IBM', '080020': 'Sun', '080011': 'Novell',
            '08001E': 'Apple', '08002B': 'DEC', '00A0C9': 'Intel',
            '00AA00': 'Intel', '00E0FC': 'D-Link', '00E091': 'Netgear'
        }

        # Частоты каналов
        self.channel_frequencies = {
            1: 2412, 2: 2417, 3: 2422, 4: 2427, 5: 2432,
            6: 2437, 7: 2442, 8: 2447, 9: 2452, 10: 2457,
            11: 2462, 12: 2467, 13: 2472, 14: 2484,
            36: 5180, 40: 5200, 44: 5220, 48: 5240,
            52: 5260, 56: 5280, 60: 5300, 64: 5320,
            100: 5500, 104: 5520, 108: 5540, 112: 5560,
            116: 5580, 120: 5600, 124: 5620, 128: 5640,
            132: 5660, 136: 5680, 140: 5700, 149: 5745,
            153: 5765, 157: 5785, 161: 5805, 165: 5825
        }

    def create_scanner_window(self, parent_window=None):
        """
        Создание окна сканера Wi-Fi
        """
        if parent_window:
            dialog = tk.Toplevel(parent_window)
        else:
            dialog = tk.Tk()
            dialog.title("Wi-Fi Scanner")

        dialog.title("Сканер Wi-Fi")
        dialog.geometry("1000x700")
        dialog.resizable(True, True)

        # Основной заголовок
        ttk.Label(dialog, text="Сканер Wi-Fi сетей",
                  font=('Arial', 14, 'bold')).pack(pady=10)

        # Основной фрейм
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Панель управления
        control_frame = self._create_control_panel(main_frame, dialog)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # Список сетей
        networks_frame = self._create_networks_list(main_frame)
        networks_frame.pack(fill=tk.BOTH, expand=True)

        # Информационная панель
        info_frame = self._create_info_panel(main_frame)
        info_frame.pack(fill=tk.X, pady=(10, 5))

        # Детали сети
        details_frame = self._create_details_panel(main_frame)
        details_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))

        # Кнопки действий
        btn_frame = self._create_action_buttons(dialog)
        btn_frame.pack(pady=10)

        # Начинаем обработку очереди сообщений
        self._process_gui_queue(dialog)

        # Автозапуск сканирования
        dialog.after(500, lambda: self._start_scan_thread())

        return dialog

    def _process_gui_queue(self, dialog):
        """Обработка сообщений из очереди для обновления GUI"""
        try:
            while True:
                # Получаем сообщение без блокировки
                func, args = self.gui_queue.get_nowait()
                # Выполняем функцию в главном потоке
                func(*args)
        except queue.Empty:
            pass
        # Повторяем каждые 100 мс
        dialog.after(100, lambda: self._process_gui_queue(dialog))

    def _update_gui(self, method, *args, **kwargs):
        """Безопасное обновление GUI из другого потока"""
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.after(0, lambda: method(*args, **kwargs))

    def _start_scan_thread(self):
        """Запуск сканирования в отдельном потоке"""
        if self.scanning:
            return tk.messagebox.showinfo("Wi-Fi Scanner", "Уже сканируется")
        tk.messagebox.showinfo('Сканирование', "Сканирование началось")
        self.scanning = True
        scan_thread = threading.Thread(
            target=self.scan_wifi,
            name="scan_wifi",
            daemon=True
        )
        scan_thread.start()


    def _create_control_panel(self, parent, dialog):
        """Создание панели управления"""
        frame = ttk.Frame(parent)

        # Кнопки управления
        ttk.Button(frame, text="🔄 Сканировать",
                  command=lambda: self._start_scan_thread()).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="⏹️ Остановить",
                  command=self.stop_scan).pack(side=tk.LEFT, padx=5)

        # Параметры сканирования
        ttk.Label(frame, text="   Интервал:").pack(side=tk.LEFT, padx=(20, 5))

        self.scan_interval_var = tk.StringVar(value=self.scan_interval)
        interval_spinbox = ttk.Spinbox(frame, from_=5, to=300,
                                      textvariable=self.scan_interval_var,
                                      width=5, command=lambda: self._update_interval())
        interval_spinbox.pack(side=tk.LEFT, padx=5)
        ttk.Label(frame, text="сек").pack(side=tk.LEFT)

        self.auto_scan_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Автосканирование",
                       variable=self.auto_scan_var).pack(side=tk.LEFT, padx=20)

        # Фильтр
        ttk.Label(frame, text="   Фильтр:").pack(side=tk.LEFT, padx=(20, 5))
        self.filter_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.filter_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="Применить",
                  command=lambda: self._apply_filter()).pack(side=tk.LEFT)

        return frame

    def _create_networks_list(self, parent):
        """Создание списка сетей"""
        frame = ttk.LabelFrame(parent, text="Обнаруженные сети", padding="10")

        # Определение колонок
        columns = ('ssid', 'bssid', 'channel', 'frequency', 'signal',
                  'security', 'encryption', 'vendor')

        self.wifi_tree = ttk.Treeview(frame, columns=columns,
                                     show='headings', height=15)

        # Настройка заголовков колонок
        columns_config = [
            ('ssid', 'Имя сети', 150),
            ('bssid', 'BSSID (MAC)', 150),
            ('channel', 'Канал', 80),
            ('frequency', 'Частота', 100),
            ('signal', 'Сигнал', 100),
            ('security', 'Безопасность', 120),
            ('encryption', 'Шифрование', 120),
            ('vendor', 'Производитель', 150)
        ]

        for col_id, heading, width in columns_config:
            self.wifi_tree.heading(col_id, text=heading)
            self.wifi_tree.column(col_id, width=width, minwidth=50)

        # Привязка событий
        self.wifi_tree.bind('<Double-1>', self._on_tree_select)
        self.wifi_tree.bind('<<TreeviewSelect>>', self._on_tree_select)

        # Скроллбары
        v_scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL,
                                   command=self.wifi_tree.yview)
        h_scrollbar = ttk.Scrollbar(frame, orient=tk.HORIZONTAL,
                                   command=self.wifi_tree.xview)
        self.wifi_tree.configure(yscrollcommand=v_scrollbar.set,
                               xscrollcommand=h_scrollbar.set)

        self.wifi_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Настройка тегов для цветового кодирования
        self._setup_tree_tags()

        return frame

    def _create_info_panel(self, parent):
        """Создание информационной панели"""
        frame = ttk.Frame(parent)

        self.status_label = ttk.Label(frame, text="Готов к сканированию",
                                     foreground="blue")
        self.status_label.pack(side=tk.LEFT)

        self.networks_count_label = ttk.Label(frame, text="Найдено сетей: 0")
        self.networks_count_label.pack(side=tk.RIGHT)

        return frame

    def _create_details_panel(self, parent):
        """Создание панели деталей сети"""
        frame = ttk.LabelFrame(parent, text="Информация о выбранной сети",
                              padding="10")

        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.wifi_details = scrolledtext.ScrolledText(text_frame, height=8,
                                                     wrap=tk.WORD)
        self.wifi_details.pack(fill=tk.BOTH, expand=True)
        self.wifi_details.insert('1.0', "Выберите сеть для просмотра подробной информации")

        return frame

    def _create_action_buttons(self, parent):
        """Создание кнопок действий"""
        frame = ttk.Frame(parent)

        ttk.Button(frame, text="📊 Анализ безопасности",
                  command=self.analyze_security).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="💾 Экспорт",
                  command=self.export_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="📈 Графики",
                  command=self.show_graphs).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="🔄 Пересканировать",
                  command=lambda: self._start_scan_thread(parent)).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="❌ Закрыть",
                  command=parent.destroy).pack(side=tk.LEFT, padx=5)

        return frame

    def _setup_tree_tags(self):
        """Настройка тегов для цветового кодирования"""
        self.wifi_tree.tag_configure('secure', background='#d4edda')
        self.wifi_tree.tag_configure('good', background='#fff3cd')
        self.wifi_tree.tag_configure('medium', background='#ffeeba')
        self.wifi_tree.tag_configure('weak', background='#f8d7da')
        self.wifi_tree.tag_configure('insecure', background='#f5c6cb')
        self.wifi_tree.tag_configure('hidden', background='#e9ecef')

    def _on_tree_select(self, event=None):
        """Обработка выбора сети в дереве"""
        selection = self.wifi_tree.selection()
        if selection:
            item = self.wifi_tree.item(selection[0])
            self.selected_network = item['values']
            self._show_network_details(item['values'])

    def _update_interval(self):
        """Обновление интервала сканирования"""
        self.scan_interval = self.scan_interval_var.get()

    def _apply_filter(self):
        """Применение фильтра к списку сетей"""
        filter_text = self.filter_var.get().lower()

        for item in self.wifi_tree.get_children():
            values = self.wifi_tree.item(item)['values']
            if values:
                # Проверяем SSID и BSSID на соответствие фильтру
                ssid = str(values[0]).lower()
                bssid = str(values[1]).lower()
                vendor = str(values[7]).lower()

                if (filter_text in ssid or
                    filter_text in bssid or
                    filter_text in vendor or
                    not filter_text):
                    self.wifi_tree.item(item, tags=())
                else:
                    self.wifi_tree.item(item, tags=('hidden',))


    def scan_wifi(self):
        """Сканирование Wi-Fi сетей в отдельном потоке"""
        try:
            # Обновляем статус через очередь
            self._update_gui(
                self.status_label.config,
                text="Сканирование...",
                foreground="orange"
            )

            # Очистка текущего списка
            self._update_gui(self._clear_wifi_tree)

            # Получение списка сетей
            networks = self._get_wifi_networks()
            self.current_wifi_networks = networks

            # Сортировка по силе сигнала
            networks.sort(key=lambda x: x.get('signal_strength', 0), reverse=True)

            # Добавление в Treeview
            for network in networks:
                values = (
                    network.get('ssid', ''),
                    network.get('bssid', ''),
                    network.get('channel', ''),
                    network.get('frequency', ''),
                    network.get('signal', ''),
                    network.get('security', ''),
                    network.get('encryption', ''),
                    network.get('vendor', '')
                )
                self._update_gui(self._add_wifi_item, values, network)

            # Обновление счетчика
            self._update_gui(
                self.networks_count_label.config,
                text=f"Найдено сетей: {len(networks)}"
            )

            # После завершения сканирования
            self._update_gui(
                self.status_label.config,
                text=f"Сканирование завершено ({len(networks)} сетей)",
                foreground="green"
            )

            # Автоповтор если включено
            if hasattr(self, 'auto_scan_var') and self.auto_scan_var.get():
                interval = int(self.scan_interval) * 1000  # в миллисекундах
                self._update_gui(self._schedule_scan, interval)

            return networks

        except Exception as e:
            self._update_gui(
                self.status_label.config,
                text=f"Ошибка сканирования: {str(e)[:50]}...",
                foreground="red"
            )
            return []

        finally:
            self.scanning = False

    # Вспомогательные методы для работы с GUI через очередь
    def _clear_wifi_tree(self):
        """Очистка Treeview"""
        if self.wifi_tree:
            for item in self.wifi_tree.get_children():
                self.wifi_tree.delete(item)

    def _add_wifi_item(self, values, network):
        """Добавление элемента в Treeview"""
        if self.wifi_tree:
            item_id = self.wifi_tree.insert('', 'end', values=values)
            self._apply_security_coloring(item_id, network)

    def _schedule_scan(self, interval):
        """Планирование следующего сканирования"""
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.after(interval, self._start_scan_thread)


    def _get_wifi_networks(self) -> List[Dict[str, Any]]:
        """
        Получение списка Wi-Fi сетей в зависимости от ОС

        Returns:
            List[Dict]: Список обнаруженных Wi-Fi сетей
        """
        current_os = platform.system()

        if current_os == 'Windows':
            return self._scan_windows()
        elif current_os == 'Linux':
            return self._scan_linux()
        elif current_os == 'Darwin':  # macOS
            return self._scan_macos()
        else:
            return self._generate_test_networks()

    def _scan_windows(self) -> List[Dict[str, Any]]:
        """Сканирование Wi-Fi на Windows с помощью netsh"""
        networks = []

        try:
            # Команда для получения списка Wi-Fi сетей
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'networks', 'mode=bssid'],
                capture_output=True,
                text=True,
                encoding='cp866',
                timeout=15
            )

            if result.returncode != 0:
                # Попробуем альтернативную команду
                result = subprocess.run(
                    ['netsh', 'wlan', 'show', 'networks'],
                    capture_output=True,
                    text=True,
                    encoding='cp866',
                    timeout=10
                )

            output = result.stdout

            # Разбор вывода netsh
            current_network = {}
            networks_data = []

            # Разделяем на секции сетей
            sections = re.split(r'\n\s*\n', output)

            for section in sections:
                lines = section.strip().split('\n')
                if not lines:
                    continue

                network_data = {}
                bssid_section = False

                for line in lines:
                    line = line.strip()

                    if 'SSID' in line and ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) > 1:
                            network_data['ssid'] = parts[1].strip()

                    elif 'BSSID' in line and ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) > 1:
                            network_data['bssid'] = parts[1].strip()
                            bssid_section = True

                    elif bssid_section:
                        if ('Signal' in line or 'Сигнал' in line) and ':' in line:
                            parts = line.split(':', 1)
                            if len(parts) > 1:
                                signal_str = parts[1].strip()
                                network_data['signal_raw'] = signal_str
                                # Преобразуем в dBm
                                if '%' in signal_str:
                                    try:
                                        percent = int(re.search(r'(\d+)%', signal_str).group(1))
                                        dbm = -100 + (percent * 0.65)
                                        network_data['signal'] = f"{dbm:.1f} dBm"
                                        network_data['signal_strength'] = percent
                                    except:
                                        network_data['signal'] = signal_str
                                        network_data['signal_strength'] = 0

                        elif ('Channel' in line or 'Канал' in line) and ':' in line:
                            parts = line.split(':', 1)
                            if len(parts) > 1:
                                channel_str = parts[1].strip()
                                network_data['channel'] = channel_str
                                # Рассчитываем частоту
                                if channel_str.isdigit():
                                    channel = int(channel_str)
                                    freq = self.channel_frequencies.get(channel)
                                    if freq:
                                        if channel <= 14:
                                            network_data['frequency'] = f"{freq} MHz (2.4 GHz)"
                                        else:
                                            network_data['frequency'] = f"{freq} MHz (5 GHz)"

                        elif ('Authentication' in line or 'Тип' in line or
                              'Security' in line or 'Шифрование' in line) and ':' in line:
                            parts = line.split(':', 1)
                            if len(parts) > 1:
                                security = parts[1].strip()
                                network_data['security'] = security

                                # Определяем тип шифрования
                                if 'WPA3' in security.upper():
                                    network_data['encryption'] = 'WPA3'
                                elif 'WPA2' in security.upper():
                                    network_data['encryption'] = 'AES (WPA2)'
                                elif 'WPA' in security.upper():
                                    network_data['encryption'] = 'TKIP/AES'
                                elif 'WEP' in security.upper():
                                    network_data['encryption'] = 'WEP'
                                else:
                                    network_data['encryption'] = 'Нет'

                if network_data:
                    networks_data.append(network_data)

            # Обработка собранных данных
            for net in networks_data:
                network = {
                    'ssid': net.get('ssid', 'Скрытая сеть'),
                    'bssid': net.get('bssid', 'Неизвестно'),
                    'channel': net.get('channel', '?'),
                    'frequency': net.get('frequency', '?'),
                    'signal': net.get('signal', '?'),
                    'signal_strength': net.get('signal_strength', 0),
                    'security': net.get('security', 'Неизвестно'),
                    'encryption': net.get('encryption', '?'),
                    'vendor': self._get_vendor_by_mac(net.get('bssid', ''))
                }
                networks.append(network)

        except Exception as e:
            print(f"Ошибка сканирования Windows Wi-Fi: {e}")
            networks = self._generate_test_networks()

        return networks

    def _scan_linux(self) -> List[Dict[str, Any]]:
        """Сканирование Wi-Fi на Linux"""
        networks = []

        try:
            # Попробуем использовать iw (требует sudo)
            try:
                result = subprocess.run(
                    ['sudo', 'iw', 'dev', 'wlan0', 'scan'],  # или wlan1 и т.д.
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    return self._parse_iw_output(result.stdout)
            except:
                pass

            # Попробуем nmcli (NetworkManager)
            try:
                result = subprocess.run(
                    ['nmcli', '-t', '-f', 'SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY',
                     'device', 'wifi', 'list'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    return self._parse_nmcli_output(result.stdout)
            except:
                pass

            # Если ничего не сработало, используем тестовые данные
            networks = self._generate_test_networks()

        except Exception as e:
            print(f"Ошибка сканирования Linux Wi-Fi: {e}")
            networks = self._generate_test_networks()

        return networks

    def _scan_macos(self) -> List[Dict[str, Any]]:
        """Сканирование Wi-Fi на macOS"""
        networks = []

        try:
            # Используем airport утилиту
            result = subprocess.run(
                ['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-s'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return self._parse_airport_output(result.stdout)
            else:
                networks = self._generate_test_networks()

        except Exception as e:
            print(f"Ошибка сканирования macOS Wi-Fi: {e}")
            networks = self._generate_test_networks()

        return networks

    def _parse_iw_output(self, output: str) -> List[Dict[str, Any]]:
        """Парсинг вывода команды iw (Linux)"""
        networks = []
        current_network = {}

        for line in output.split('\n'):
            line = line.strip()

            if 'BSS' in line and '(' in line:
                if current_network:
                    networks.append(current_network)
                    current_network = {}

                # Извлекаем MAC-адрес
                bssid_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', line)
                if bssid_match:
                    current_network['bssid'] = bssid_match.group(0)

            elif 'SSID:' in line:
                ssid_match = re.search(r'SSID:\s*(.+)', line)
                if ssid_match:
                    current_network['ssid'] = ssid_match.group(1).strip()

            elif 'freq:' in line:
                freq_match = re.search(r'freq:\s*(\d+)', line)
                if freq_match:
                    freq = int(freq_match.group(1))
                    current_network['frequency'] = f"{freq} MHz"
                    # Определяем канал по частоте
                    for chan, chan_freq in self.channel_frequencies.items():
                        if abs(freq - chan_freq) <= 10:
                            current_network['channel'] = str(chan)
                            break

            elif 'signal:' in line:
                signal_match = re.search(r'signal:\s*([-\d.]+)\s*dBm', line)
                if signal_match:
                    signal = float(signal_match.group(1))
                    current_network['signal'] = f"{signal:.1f} dBm"
                    current_network['signal_strength'] = self._dbm_to_percent(signal)

        # Добавляем последнюю сеть
        if current_network:
            networks.append(current_network)

        # Заполняем недостающие поля
        for net in networks:
            net.setdefault('ssid', 'Скрытая сеть')
            net.setdefault('bssid', 'Неизвестно')
            net.setdefault('channel', '?')
            net.setdefault('frequency', '?')
            net.setdefault('signal', '?')
            net.setdefault('signal_strength', 0)
            net.setdefault('security', 'Неизвестно')
            net.setdefault('encryption', '?')
            net.setdefault('vendor', self._get_vendor_by_mac(net.get('bssid', '')))

        return networks

    def _parse_nmcli_output(self, output: str) -> List[Dict[str, Any]]:
        """Парсинг вывода команды nmcli (Linux)"""
        networks = []

        for line in output.strip().split('\n'):
            if not line:
                continue

            parts = line.split(':')
            if len(parts) >= 6:
                network = {
                    'ssid': parts[0] if parts[0] else 'Скрытая сеть',
                    'bssid': parts[1] if len(parts) > 1 else 'Неизвестно',
                    'channel': parts[2] if len(parts) > 2 else '?',
                    'frequency': parts[3] if len(parts) > 3 else '?',
                    'signal': f"{parts[4]}%" if len(parts) > 4 else '?',
                    'signal_strength': int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0,
                    'security': parts[5] if len(parts) > 5 else 'Неизвестно',
                    'encryption': 'AES' if 'WPA2' in parts[5] else 'TKIP' if 'WPA' in parts[5] else '?',
                    'vendor': self._get_vendor_by_mac(parts[1] if len(parts) > 1 else '')
                }
                networks.append(network)

        return networks

    def _parse_airport_output(self, output: str) -> List[Dict[str, Any]]:
        """Парсинг вывода команды airport (macOS)"""
        networks = []
        lines = output.strip().split('\n')

        if len(lines) <= 1:
            return networks

        # Пропускаем заголовок
        for line in lines[1:]:
            parts = re.split(r'\s{2,}', line.strip())
            if len(parts) >= 6:
                network = {
                    'ssid': parts[0] if parts[0] else 'Скрытая сеть',
                    'bssid': parts[1] if len(parts) > 1 else 'Неизвестно',
                    'channel': parts[3] if len(parts) > 3 else '?',
                    'frequency': self._channel_to_freq(parts[3]) if len(parts) > 3 else '?',
                    'signal': f"{parts[2]} dBm" if len(parts) > 2 else '?',
                    'signal_strength': self._dbm_to_percent(float(parts[2])) if len(parts) > 2 and parts[2].replace('-', '').isdigit() else 0,
                    'security': parts[5] if len(parts) > 5 else 'Неизвестно',
                    'encryption': 'AES' if 'WPA2' in parts[5] else 'TKIP' if 'WPA' in parts[5] else 'WEP' if 'WEP' in parts[5] else '?',
                    'vendor': self._get_vendor_by_mac(parts[1] if len(parts) > 1 else '')
                }
                networks.append(network)

        return networks

    def _generate_test_networks(self, count=12) -> List[Dict[str, Any]]:
        """
        Генерация тестовых данных для демонстрации

        Args:
            count: Количество тестовых сетей

        Returns:
            List[Dict]: Список тестовых сетей
        """
        import random
        networks = []

        vendors = ["TP-Link", "ASUS", "D-Link", "Huawei", "Xiaomi",
                  "Zyxel", "Netgear", "MikroTik", "Ubiquiti", "Cisco"]
        ssid_prefixes = ["HomeNet", "Office", "FreeWiFi", "MTS", "Beeline",
                        "Yota", "TP-Link_", "DLink_", "ASUS_", "Guest",
                        "AndroidAP", "iPhone", "Xiaomi_", "Huawei-"]
        channels_24ghz = ["1", "6", "11"]
        channels_5ghz = ["36", "40", "44", "48", "149", "153", "157"]
        securities = ["WPA2", "WPA3", "WPA2/WPA3", "WEP", "Открытая", "WPA"]

        for i in range(count):
            is_5ghz = random.choice([False, False, False, True])  # Чаще 2.4GHz

            network = {
                'ssid': f"{random.choice(ssid_prefixes)}{random.randint(1, 999)}",
                'bssid': f"{random.randint(0xAA, 0xFF):02X}:{random.randint(0xAA, 0xFF):02X}:"
                        f"{random.randint(0xAA, 0xFF):02X}:{random.randint(0xAA, 0xFF):02X}:"
                        f"{random.randint(0xAA, 0xFF):02X}:{random.randint(0xAA, 0xFF):02X}",
                'channel': random.choice(channels_5ghz if is_5ghz else channels_24ghz),
                'frequency': f"{random.choice([2412, 2437, 2462, 5180, 5200, 5220, 5745, 5765, 5785])} MHz",
                'signal': f"-{random.randint(35, 85)} dBm",
                'signal_strength': random.randint(25, 95),
                'security': random.choice(securities),
                'encryption': random.choice(["AES", "TKIP", "AES/TKIP", "WEP", ""]),
                'vendor': random.choice(vendors)
            }

            # Корректируем частоту в зависимости от канала
            if network['channel'].isdigit():
                chan = int(network['channel'])
                freq = self.channel_frequencies.get(chan)
                if freq:
                    network['frequency'] = f"{freq} MHz ({'5' if chan > 14 else '2.4'} GHz)"

            networks.append(network)

        return networks

    def _get_vendor_by_mac(self, mac_address: str) -> str:
        """
        Определение производителя по MAC-адресу

        Args:
            mac_address: MAC-адрес в формате XX:XX:XX:XX:XX:XX

        Returns:
            str: Название производителя
        """
        if not mac_address or mac_address == 'Неизвестно':
            return 'Неизвестно'

        # Очищаем MAC-адрес
        mac_clean = mac_address.replace(':', '').replace('-', '').upper()
        if len(mac_clean) < 6:
            return 'Неизвестно'

        # Ищем по префиксу
        prefix = mac_clean[:6]
        return self.vendor_db.get(prefix, 'Неизвестно')

    def _dbm_to_percent(self, dbm: float) -> int:
        """
        Преобразование dBm в проценты

        Args:
            dbm: Уровень сигнала в dBm

        Returns:
            int: Уровень сигнала в процентах (0-100)
        """
        # Приблизительное преобразование
        if dbm >= -50:
            return 100
        elif dbm >= -60:
            return 80
        elif dbm >= -70:
            return 60
        elif dbm >= -80:
            return 40
        elif dbm >= -90:
            return 20
        else:
            return 10

    def _channel_to_freq(self, channel: str) -> str:
        """
        Преобразование канала в частоту

        Args:
            channel: Номер канала

        Returns:
            str: Частота в MHz
        """
        if channel.isdigit():
            chan = int(channel)
            freq = self.channel_frequencies.get(chan)
            if freq:
                return f"{freq} MHz ({'5' if chan > 14 else '2.4'} GHz)"

        return "?"

    def _apply_security_coloring(self, item_id: str, network: Dict[str, Any]):
        """
        Применение цветового кодирования по уровню безопасности

        Args:
            item_id: ID элемента в Treeview
            network: Данные сети
        """
        security = str(network.get('security', '')).lower()

        if 'wpa3' in security:
            self.wifi_tree.item(item_id, tags=('secure',))
        elif 'wpa2' in security:
            self.wifi_tree.item(item_id, tags=('good',))
        elif 'wpa' in security:
            self.wifi_tree.item(item_id, tags=('medium',))
        elif 'wep' in security:
            self.wifi_tree.item(item_id, tags=('weak',))
        elif 'открыт' in security or 'open' in security:
            self.wifi_tree.item(item_id, tags=('insecure',))

    def _show_network_details(self, values):
        """
        Показать детали выбранной сети

        Args:
            values: Значения выбранной строки
        """
        if not values or not hasattr(self, 'wifi_details'):
            return

        details_text = f"""
=== Информация о Wi-Fi сети ===

Имя сети (SSID): {values[0]}
MAC-адрес (BSSID): {values[1]}
Канал: {values[2]}
Частота: {values[3]}
Уровень сигнала: {values[4]}
Тип безопасности: {values[5]}
Тип шифрования: {values[6]}
Производитель оборудования: {values[7]}

--- Анализ безопасности ---
"""

        # Анализ безопасности
        security = str(values[5]).lower()
        if 'wpa3' in security:
            details_text += "✓ ВЫСОКИЙ УРОВЕНЬ БЕЗОПАСНОСТИ (WPA3)\n"
            details_text += "• Последний стандарт безопасности\n"
            details_text += "• Защита от атак методом перебора\n"
            details_text += "• Forward secrecy для каждого клиента\n"
            details_text += "✓ Рекомендуется для использования\n"

        elif 'wpa2' in security:
            details_text += "✓ ХОРОШИЙ УРОВЕНЬ БЕЗОПАСНОСТИ (WPA2)\n"
            details_text += "• Проверенный стандарт\n"
            details_text += "• Шифрование AES\n"
            details_text += "• Уязвим к атакам KRACK (требуются патчи)\n"
            details_text += "✓ Приемлемо для большинства задач\n"

        elif 'wpa' in security:
            details_text += "⚠ СРЕДНИЙ УРОВЕНЬ БЕЗОПАСНОСТИ (WPA)\n"
            details_text += "• Устаревший стандарт\n"
            details_text += "• Шифрование TKIP (менее безопасно)\n"
            details_text += "• Уязвим к различным атакам\n"
            details_text += "⚠ Рекомендуется обновить до WPA2/WPA3\n"

        elif 'wep' in security:
            details_text += "✗ НИЗКИЙ УРОВЕНЬ БЕЗОПАСНОСТИ (WEP)\n"
            details_text += "• Очень старый и небезопасный\n"
            details_text += "• Шифрование можно взломать за минуты\n"
            details_text += "• Не соответствует современным стандартам\n"
            details_text += "✗ НЕ рекомендуется к использованию\n"

        elif 'открыт' in security or 'open' in security:
            details_text += "✗ ОТКРЫТАЯ СЕТЬ - НЕТ ЗАЩИТЫ\n"
            details_text += "• Все данные передаются в открытом виде\n"
            details_text += "• Легко прослушивается\n"
            details_text += "• Любой может подключиться\n"
            details_text += "✗ Используйте только с VPN\n"

        else:
            details_text += "⚠ НЕИЗВЕСТНЫЙ ТИП БЕЗОПАСНОСТИ\n"
            details_text += "⚠ Будьте осторожны при подключении\n"
            details_text += "⚠ Рекомендуется избегать\n"

        # Анализ силы сигнала
        signal_str = str(values[4])
        if 'dBm' in signal_str:
            try:
                signal_value = float(signal_str.split()[0])
                if signal_value >= -50:
                    details_text += "\n✓ ОТЛИЧНЫЙ СИГНАЛ\n"
                    details_text += "• Стабильное соединение\n"
                    details_text += "• Высокая скорость передачи\n"
                elif signal_value >= -67:
                    details_text += "\n✓ ХОРОШИЙ СИГНАЛ\n"
                    details_text += "• Надежное соединение\n"
                    details_text += "• Хорошая скорость\n"
                elif signal_value >= -70:
                    details_text += "\n⚠ СРЕДНИЙ СИГНАЛ\n"
                    details_text += "• Возможны обрывы\n"
                    details_text += "• Скорость может падать\n"
                elif signal_value >= -80:
                    details_text += "\n⚠ СЛАБЫЙ СИГНАЛ\n"
                    details_text += "• Частые обрывы\n"
                    details_text += "• Низкая скорость\n"
                else:
                    details_text += "\n✗ ОЧЕНЬ СЛАБЫЙ СИГНАЛ\n"
                    details_text += "• Нестабильное соединение\n"
                    details_text += "• Практически непригоден\n"
            except:
                pass

        details_text += f"\nВремя обнаружения: {datetime.now().strftime('%H:%M:%S')}"
        details_text += f"\nДата: {datetime.now().strftime('%d.%m.%Y')}"

        self.wifi_details.delete('1.0', tk.END)
        self.wifi_details.insert('1.0', details_text)

    def stop_scan(self):
        """Остановка сканирования"""
        self.scanning = False
        if hasattr(self, 'status_label'):
            self.status_label.config(text="Сканирование остановлено", foreground="red")

    def analyze_security(self):
        """
        Анализ безопасности всех обнаруженных сетей

        Returns:
            Dict: Результаты анализа
        """
        if not self.current_wifi_networks:
            messagebox.showwarning("Нет данных", "Сначала выполните сканирование!")
            return None

        # Создание окна анализа
        analysis_window = tk.Toplevel()
        analysis_window.title("Анализ безопасности Wi-Fi сетей")
        analysis_window.geometry("700x600")

        ttk.Label(analysis_window, text="Анализ безопасности Wi-Fi сетей",
                 font=('Arial', 12, 'bold')).pack(pady=10)

        # Статистика
        stats_frame = ttk.LabelFrame(analysis_window, text="Статистика", padding="10")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)

        total = len(self.current_wifi_networks)
        security_stats = defaultdict(int)
        weak_networks = []
        open_networks = []

        for network in self.current_wifi_networks:
            security = str(network.get('security', '')).lower()

            if 'wpa3' in security:
                security_stats['WPA3'] += 1
            elif 'wpa2' in security:
                security_stats['WPA2'] += 1
            elif 'wpa' in security:
                security_stats['WPA'] += 1
                weak_networks.append(network)
            elif 'wep' in security:
                security_stats['WEP'] += 1
                weak_networks.append(network)
            elif 'открыт' in security or 'open' in security:
                security_stats['Открытые'] += 1
                open_networks.append(network)
                weak_networks.append(network)
            else:
                security_stats['Неизвестно'] += 1

        # Расчет процентов
        stats_percent = {}
        for key, value in security_stats.items():
            stats_percent[key] = (value / total * 100) if total > 0 else 0

        # Отображение статистики
        stats_text = f"""
Общее количество сетей: {total}

Распределение по типам безопасности:
────────────────────────────────────
WPA3 (наиболее безопасно): {security_stats.get('WPA3', 0)} сетей ({stats_percent.get('WPA3', 0):.1f}%)
WPA2 (безопасно): {security_stats.get('WPA2', 0)} сетей ({stats_percent.get('WPA2', 0):.1f}%)
WPA (устаревшее): {security_stats.get('WPA', 0)} сетей ({stats_percent.get('WPA', 0):.1f}%)
WEP (очень слабо): {security_stats.get('WEP', 0)} сетей ({stats_percent.get('WEP', 0):.1f}%)
Открытые сети (опасно): {security_stats.get('Открытые', 0)} сетей ({stats_percent.get('Открытые', 0):.1f}%)
Неизвестный тип: {security_stats.get('Неизвестно', 0)} сетей ({stats_percent.get('Неизвестно', 0):.1f}%)

Уязвимые сети (WEP/Открытые/WPA): {len(weak_networks)} ({len(weak_networks)/total*100:.1f}%)
        """

        stats_label = ttk.Label(stats_frame, text=stats_text, justify=tk.LEFT)
        stats_label.pack()

        # Рекомендации
        recommendations_frame = ttk.LabelFrame(analysis_window, text="Рекомендации", padding="10")
        recommendations_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        recommendations = scrolledtext.ScrolledText(recommendations_frame, height=12)
        recommendations.pack(fill=tk.BOTH, expand=True)

        rec_text = "=== РЕКОМЕНДАЦИИ ПО БЕЗОПАСНОСТИ WI-FI ===\n\n"

        # Оценка общей безопасности
        secure_percent = (security_stats.get('WPA3', 0) + security_stats.get('WPA2', 0)) / total * 100
        insecure_percent = (security_stats.get('Открытые', 0) + security_stats.get('WEP', 0)) / total * 100

        if secure_percent >= 70:
            rec_text += "📊 ОБЩАЯ ОЦЕНКА: ХОРОШАЯ\n"
            rec_text += "Большинство сетей используют современные стандарты безопасности.\n\n"
        elif secure_percent >= 40:
            rec_text += "📊 ОБЩАЯ ОЦЕНКА: СРЕДНЯЯ\n"
            rec_text += "Есть как безопасные, так и уязвимые сети в окружении.\n\n"
        else:
            rec_text += "📊 ОБЩАЯ ОЦЕНКА: НИЗКАЯ\n"
            rec_text += "Много уязвимых сетей в окружении. Будьте осторожны!\n\n"

        if security_stats.get('WPA3', 0) > 0:
            rec_text += "✓ Обнаружены сети с WPA3 - отличная защита\n"

        if security_stats.get('WPA2', 0) > 0:
            rec_text += "✓ Сети с WPA2 обеспечивают хорошую защиту\n"

        if security_stats.get('WPA', 0) > 0:
            rec_text += f"⚠ {security_stats.get('WPA', 0)} сетей с устаревшим WPA\n"
            rec_text += "  Рекомендуется обновить до WPA2/WPA3\n"

        if len(weak_networks) > 0:
            rec_text += f"\n⚠ ВНИМАНИЕ! Обнаружены {len(weak_networks)} уязвимых сетей:\n"
            for i, network in enumerate(weak_networks[:5], 1):
                rec_text += f"   {i}. {network.get('ssid', '')} ({network.get('security', '')})\n"
            if len(weak_networks) > 5:
                rec_text += f"   ... и еще {len(weak_networks) - 5}\n"

            rec_text += "\n✗ НЕ подключайтесь к этим сетям для передачи конфиденциальных данных!\n"

        rec_text += "\n🔒 ОБЩИЕ РЕКОМЕНДАЦИИ:\n"
        rec_text += "1. Всегда используйте WPA3 или WPA2 с шифрованием AES\n"
        rec_text += "2. Избегайте открытых Wi-Fi сетей для важных операций\n"
        rec_text += "3. Используйте VPN при работе в публичных сетях\n"
        rec_text += "4. Регулярно меняйте пароли Wi-Fi (раз в 3-6 месяцев)\n"
        rec_text += "5. Отключите WPS (Wi-Fi Protected Setup)\n"
        rec_text += "6. Скрывайте SSID если не требуется публичный доступ\n"
        rec_text += "7. Используйте сложные пароли (12+ символов, буквы+цифры+спецсимволы)\n"
        rec_text += "8. Отключайте гостевой доступ если он не нужен\n"

        recommendations.insert('1.0', rec_text)

        # Кнопки
        btn_frame = ttk.Frame(analysis_window)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="💾 Экспорт отчета",
                  command=lambda: self._export_security_report(
                      total, security_stats, stats_percent, weak_networks, rec_text
                  )).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть",
                  command=analysis_window.destroy).pack(side=tk.LEFT, padx=5)

        return {
            'total_networks': total,
            'security_stats': dict(security_stats),
            'security_percent': dict(stats_percent),
            'weak_networks': weak_networks,
            'open_networks': open_networks,
            'recommendations': rec_text
        }

    def export_results(self, networks=None):
        """
        Экспорт результатов сканирования

        Args:
            networks: Список сетей для экспорта (если None, используется текущий список)

        Returns:
            bool: Успех операции
        """
        if networks is None:
            networks = self.current_wifi_networks

        if not networks:
            messagebox.showwarning("Нет данных", "Сначала выполните сканирование!")
            return False

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[
                ("JSON файл", "*.json"),
                ("Текстовый файл", "*.txt"),
                ("CSV файл", "*.csv"),
                ("HTML файл", "*.html"),
                ("Все файлы", "*.*")
            ],
            title="Экспорт результатов сканирования"
        )

        if not file_path:
            return False

        try:
            export_data = {
                "scan_time": datetime.now().isoformat(),
                "scan_timestamp": datetime.now().timestamp(),
                "total_networks": len(networks),
                "operating_system": platform.system(),
                "os_version": platform.version(),
                "networks": networks
            }

            if file_path.endswith('.json'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)

            elif file_path.endswith('.txt'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    self._export_to_txt(f, networks)

            elif file_path.endswith('.csv'):
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    self._export_to_csv(f, networks)

            elif file_path.endswith('.html'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    self._export_to_html(f, networks)

            else:
                # По умолчанию JSON
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)

            messagebox.showinfo("Успех", f"Результаты экспортированы в:\n{file_path}")
            return True

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать данные:\n{str(e)}")
            return False

    def _export_to_txt(self, file_obj, networks):
        """Экспорт в текстовый формат"""
        file_obj.write("=" * 60 + "\n")
        file_obj.write("РЕЗУЛЬТАТЫ СКАНИРОВАНИЯ WI-FI СЕТЕЙ\n")
        file_obj.write("=" * 60 + "\n\n")

        file_obj.write(f"Время сканирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        file_obj.write(f"Операционная система: {platform.system()} {platform.version()}\n")
        file_obj.write(f"Всего обнаружено сетей: {len(networks)}\n\n")

        file_obj.write("СПИСОК ОБНАРУЖЕННЫХ СЕТЕЙ:\n")
        file_obj.write("-" * 60 + "\n\n")

        for i, network in enumerate(networks, 1):
            file_obj.write(f"СЕТЬ #{i}\n")
            file_obj.write(f"  Имя сети (SSID): {network.get('ssid', '')}\n")
            file_obj.write(f"  MAC-адрес (BSSID): {network.get('bssid', '')}\n")
            file_obj.write(f"  Канал: {network.get('channel', '')}\n")
            file_obj.write(f"  Частота: {network.get('frequency', '')}\n")
            file_obj.write(f"  Уровень сигнала: {network.get('signal', '')}\n")
            file_obj.write(f"  Тип безопасности: {network.get('security', '')}\n")
            file_obj.write(f"  Тип шифрования: {network.get('encryption', '')}\n")
            file_obj.write(f"  Производитель: {network.get('vendor', '')}\n")
            file_obj.write("-" * 40 + "\n\n")

    def _export_to_csv(self, file_obj, networks):
        """Экспорт в CSV формат"""
        writer = csv.writer(file_obj)

        # Заголовок
        writer.writerow(['SSID', 'BSSID', 'Channel', 'Frequency', 'Signal',
                        'Security', 'Encryption', 'Vendor', 'Signal_Strength'])

        # Данные
        for network in networks:
            writer.writerow([
                network.get('ssid', ''),
                network.get('bssid', ''),
                network.get('channel', ''),
                network.get('frequency', ''),
                network.get('signal', ''),
                network.get('security', ''),
                network.get('encryption', ''),
                network.get('vendor', ''),
                network.get('signal_strength', 0)
            ])

    def _export_to_html(self, file_obj, networks):
        """Экспорт в HTML формат"""
        file_obj.write("""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Результаты сканирования Wi-Fi</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        .info { background: #e8f5e9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th { background-color: #4CAF50; color: white; padding: 12px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #ddd; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        tr:hover { background-color: #f5f5f5; }
        .secure { background-color: #d4edda !important; }
        .good { background-color: #fff3cd !important; }
        .weak { background-color: #f8d7da !important; }
        .footer { margin-top: 30px; text-align: center; color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📡 Результаты сканирования Wi-Fi сетей</h1>
        
        <div class="info">
            <strong>Время сканирования:</strong> """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """<br>
            <strong>Операционная система:</strong> """ + platform.system() + " " + platform.version() + """<br>
            <strong>Всего обнаружено сетей:</strong> """ + str(len(networks)) + """
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>SSID</th>
                    <th>BSSID</th>
                    <th>Канал</th>
                    <th>Частота</th>
                    <th>Сигнал</th>
                    <th>Безопасность</th>
                    <th>Шифрование</th>
                    <th>Производитель</th>
                </tr>
            </thead>
            <tbody>
""")

        for network in networks:
            security = str(network.get('security', '')).lower()
            row_class = ""

            if 'wpa3' in security:
                row_class = "secure"
            elif 'wpa2' in security:
                row_class = "good"
            elif 'wep' in security or 'открыт' in security or 'open' in security:
                row_class = "weak"

            file_obj.write(f"""                <tr class="{row_class}">
                    <td>{network.get('ssid', '')}</td>
                    <td>{network.get('bssid', '')}</td>
                    <td>{network.get('channel', '')}</td>
                    <td>{network.get('frequency', '')}</td>
                    <td>{network.get('signal', '')}</td>
                    <td>{network.get('security', '')}</td>
                    <td>{network.get('encryption', '')}</td>
                    <td>{network.get('vendor', '')}</td>
                </tr>
""")

        file_obj.write("""            </tbody>
        </table>
        
        <div class="footer">
            Сгенерировано Wi-Fi Scanner • """ + datetime.now().strftime('%d.%m.%Y %H:%M:%S') + """
        </div>
    </div>
</body>
</html>""")

    def _export_security_report(self, total, security_stats, stats_percent,
                               weak_networks, recommendations):
        """Экспорт отчета безопасности"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Текстовый файл", "*.txt"),
                ("HTML файл", "*.html"),
                ("Все файлы", "*.*")
            ],
            title="Экспорт отчета безопасности"
        )

        if not file_path:
            return

        try:
            if file_path.endswith('.html'):
                self._export_security_html(file_path, total, security_stats,
                                         stats_percent, weak_networks, recommendations)
            else:
                self._export_security_txt(file_path, total, security_stats,
                                        stats_percent, weak_networks, recommendations)

            messagebox.showinfo("Успех", f"Отчет экспортирован в:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать отчет:\n{str(e)}")

    def _export_security_txt(self, file_path, total, security_stats,
                            stats_percent, weak_networks, recommendations):
        """Экспорт отчета безопасности в TXT"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("ОТЧЕТ АНАЛИЗА БЕЗОПАСНОСТИ WI-FI СЕТЕЙ\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Время анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Всего проанализировано сетей: {total}\n\n")

            f.write("СТАТИСТИКА БЕЗОПАСНОСТИ:\n")
            f.write("-" * 50 + "\n")

            for security_type in ['WPA3', 'WPA2', 'WPA', 'WEP', 'Открытые', 'Неизвестно']:
                count = security_stats.get(security_type, 0)
                percent = stats_percent.get(security_type, 0)
                f.write(f"{security_type}: {count} сетей ({percent:.1f}%)\n")

            f.write(f"\nУязвимых сетей: {len(weak_networks)} ({len(weak_networks)/total*100:.1f}%)\n\n")

            if weak_networks:
                f.write("СПИСОК УЯЗВИМЫХ СЕТЕЙ:\n")
                f.write("-" * 50 + "\n")
                for i, network in enumerate(weak_networks, 1):
                    f.write(f"{i}. {network.get('ssid', '')} - {network.get('security', '')}\n")
                f.write("\n")

            f.write(recommendations)

    def _export_security_html(self, file_path, total, security_stats,
                             stats_percent, weak_networks, recommendations):
        """Экспорт отчета безопасности в HTML"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет анализа безопасности Wi-Fi</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
               margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .report { max-width: 900px; margin: 0 auto; background: white; 
                 padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
        h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; 
             border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap: 15px; margin-bottom: 30px; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 10px; 
                    text-align: center; border-left: 5px solid #3498db; }
        .stat-value { font-size: 2em; font-weight: bold; color: #2c3e50; }
        .stat-label { color: #7f8c8d; margin-top: 5px; }
        .security-level { display: inline-block; padding: 3px 10px; border-radius: 20px; 
                         font-size: 0.8em; font-weight: bold; }
        .secure { background: #27ae60; color: white; }
        .good { background: #f39c12; color: white; }
        .weak { background: #e74c3c; color: white; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th { background: #2c3e50; color: white; padding: 12px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #ecf0f1; }
        .recommendations { background: #e8f4f8; padding: 20px; border-radius: 10px; 
                          margin-top: 30px; border-left: 5px solid #3498db; }
        .warning { background: #ffeaa7; padding: 15px; border-radius: 8px; 
                  margin: 15px 0; border-left: 5px solid #fdcb6e; }
        .footer { text-align: center; margin-top: 40px; color: #7f8c8d; 
                 font-size: 0.9em; border-top: 1px solid #ecf0f1; padding-top: 20px; }
    </style>
</head>
<body>
    <div class="report">
        <h1>📊 Отчет анализа безопасности Wi-Fi сетей</h1>
        
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 1.2em; color: #2c3e50;">
                <strong>Время анализа:</strong> """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """<br>
                <strong>Всего сетей:</strong> """ + str(total) + """
            </div>
        </div>
        
        <div class="stats">
""")

            # Карточки статистики
            stats_data = [
                ("WPA3", security_stats.get('WPA3', 0), "secure"),
                ("WPA2", security_stats.get('WPA2', 0), "good"),
                ("WPA", security_stats.get('WPA', 0), "weak"),
                ("WEP", security_stats.get('WEP', 0), "weak"),
                ("Открытые", security_stats.get('Открытые', 0), "weak"),
                ("Уязвимые", len(weak_networks), "weak" if len(weak_networks) > 0 else "secure")
            ]

            for label, value, level_class in stats_data:
                percent = (value / total * 100) if total > 0 else 0
                f.write(f"""            <div class="stat-card">
                <div class="stat-value">{value}</div>
                <div class="stat-label">{label}</div>
                <div style="margin-top: 10px;">
                    <span class="security-level {level_class}">{percent:.1f}%</span>
                </div>
            </div>
""")

            f.write("""        </div>
        
""")

            if weak_networks:
                f.write("""        <div class="warning">
            <strong>⚠ ВНИМАНИЕ!</strong> Обнаружено <strong>""" + str(len(weak_networks)) + """</strong> уязвимых сетей
        </div>
        
        <h3>Список уязвимых сетей:</h3>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>SSID</th>
                    <th>BSSID</th>
                    <th>Тип безопасности</th>
                    <th>Уровень риска</th>
                </tr>
            </thead>
            <tbody>
""")

                for i, network in enumerate(weak_networks[:10], 1):
                    security = network.get('security', 'Неизвестно')
                    risk_level = "Высокий" if 'открыт' in security.lower() or 'open' in security.lower() or 'wep' in security.lower() else "Средний"

                    f.write(f"""                <tr>
                    <td>{i}</td>
                    <td>{network.get('ssid', '')}</td>
                    <td>{network.get('bssid', '')}</td>
                    <td>{security}</td>
                    <td><span class="security-level weak">{risk_level}</span></td>
                </tr>
""")

                if len(weak_networks) > 10:
                    f.write(f"""                <tr>
                    <td colspan="5" style="text-align: center; font-style: italic;">
                        ... и еще {len(weak_networks) - 10} уязвимых сетей
                    </td>
                </tr>
""")

                f.write("""            </tbody>
        </table>
""")

            f.write("""        
        <div class="recommendations">
            <h3>🔒 Рекомендации по безопасности:</h3>
            <div style="white-space: pre-line; line-height: 1.6;">
""" + recommendations.replace('\n', '<br>') + """
            </div>
        </div>
        
        <div class="footer">
            Отчет сгенерирован Wi-Fi Scanner • """ + datetime.now().strftime('%d.%m.%Y') + """
        </div>
    </div>
</body>
</html>""")

    def show_graphs(self):
        """Показать графики анализа Wi-Fi сетей"""
        if not self.current_wifi_networks:
            messagebox.showwarning("Нет данных", "Сначала выполните сканирование!")
            return

        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import numpy as np

        except ImportError:
            messagebox.showerror("Ошибка",
                               "Для построения графиков установите matplotlib:\n"
                               "pip install matplotlib numpy")
            return

        # Создание окна графиков
        graph_window = tk.Toplevel()
        graph_window.title("Графики анализа Wi-Fi сетей")
        graph_window.geometry("1000x800")

        # Создание вкладок
        notebook = ttk.Notebook(graph_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 1. График распределения по каналам
        channels_frame = ttk.Frame(notebook)
        notebook.add(channels_frame, text="📶 Распределение по каналам")

        # 2. График силы сигнала
        signal_frame = ttk.Frame(notebook)
        notebook.add(signal_frame, text="📡 Сила сигнала")

        # 3. График безопасности
        security_frame = ttk.Frame(notebook)
        notebook.add(security_frame, text="🔒 Уровень безопасности")

        # Подготовка данных
        channels = []
        signals = []
        securities = defaultdict(list)
        security_types = defaultdict(int)

        for network in self.current_wifi_networks:
            try:
                # Каналы
                channel_str = network.get('channel', '')
                if channel_str and channel_str.isdigit():
                    channels.append(int(channel_str))

                # Сигналы
                signal_str = network.get('signal', '')
                if 'dBm' in signal_str:
                    try:
                        signal_val = float(signal_str.split()[0])
                        signals.append(signal_val)
                    except:
                        pass

                # Безопасность
                security = network.get('security', 'Неизвестно')
                security_types[security] += 1

                if 'dBm' in signal_str:
                    try:
                        signal_val = float(signal_str.split()[0])
                        securities[security].append(signal_val)
                    except:
                        pass

            except Exception as e:
                continue

        # 1. Распределение по каналам
        if channels:
            fig1, ax1 = plt.subplots(figsize=(10, 6))

            # Группируем по диапазонам
            channels_24ghz = [c for c in channels if 1 <= c <= 14]
            channels_5ghz = [c for c in channels if c > 14]

            if channels_24ghz:
                ax1.hist(channels_24ghz, bins=range(1, 15),
                        alpha=0.7, label='2.4 GHz', color='blue', edgecolor='black')

            if channels_5ghz:
                ax1.hist(channels_5ghz, bins=sorted(set(channels_5ghz)),
                        alpha=0.7, label='5 GHz', color='green', edgecolor='black')

            ax1.set_xlabel('Канал')
            ax1.set_ylabel('Количество сетей')
            ax1.set_title('Распределение Wi-Fi сетей по каналам')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            plt.tight_layout()
            canvas1 = FigureCanvasTkAgg(fig1, master=channels_frame)
            canvas1.draw()
            canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 2. Сила сигнала
        if signals:
            fig2, (ax2_1, ax2_2) = plt.subplots(1, 2, figsize=(12, 5))

            # Гистограмма распределения сигналов
            ax2_1.hist(signals, bins=20, alpha=0.7, color='orange', edgecolor='black')
            ax2_1.set_xlabel('Уровень сигнала (dBm)')
            ax2_1.set_ylabel('Количество сетей')
            ax2_1.set_title('Распределение по силе сигнала')
            ax2_1.grid(True, alpha=0.3)

            # Box plot по безопасности
            if securities:
                security_data = []
                security_labels = []

                for security_type, sig_list in securities.items():
                    if sig_list:
                        security_data.append(sig_list)
                        security_labels.append(security_type[:15])

                if security_data:
                    box = ax2_2.boxplot(security_data, labels=security_labels,
                                       patch_artist=True)

                    # Цвета для box plot
                    colors = ['lightgreen', 'lightyellow', 'lightcoral',
                             'lightblue', 'lightpink']
                    for patch, color in zip(box['boxes'], colors):
                        patch.set_facecolor(color)

                    ax2_2.set_xlabel('Тип безопасности')
                    ax2_2.set_ylabel('Уровень сигнала (dBm)')
                    ax2_2.set_title('Сила сигнала по типам безопасности')
                    ax2_2.grid(True, alpha=0.3)
                    plt.setp(ax2_2.get_xticklabels(), rotation=45, ha='right')

            plt.tight_layout()
            canvas2 = FigureCanvasTkAgg(fig2, master=signal_frame)
            canvas2.draw()
            canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 3. Уровень безопасности
        if security_types:
            fig3, (ax3_1, ax3_2) = plt.subplots(1, 2, figsize=(12, 5))

            # Круговая диаграмма
            labels = list(security_types.keys())
            sizes = list(security_types.values())

            # Группируем маленькие значения
            threshold = sum(sizes) * 0.05  # 5%
            other_sum = 0
            new_labels = []
            new_sizes = []

            for label, size in zip(labels, sizes):
                if size >= threshold:
                    new_labels.append(label)
                    new_sizes.append(size)
                else:
                    other_sum += size

            if other_sum > 0:
                new_labels.append('Другие')
                new_sizes.append(other_sum)

            colors = plt.cm.Set3(np.linspace(0, 1, len(new_labels)))
            ax3_1.pie(new_sizes, labels=new_labels, autopct='%1.1f%%',
                     colors=colors, startangle=90)
            ax3_1.set_title('Распределение по типам безопасности')
            ax3_1.axis('equal')

            # Столбчатая диаграмма
            security_categories = {
                'WPA3': 0,
                'WPA2': 0,
                'WPA': 0,
                'WEP': 0,
                'Открытые': 0,
                'Неизвестно': 0
            }

            for security, count in security_types.items():
                security_lower = security.lower()
                if 'wpa3' in security_lower:
                    security_categories['WPA3'] += count
                elif 'wpa2' in security_lower:
                    security_categories['WPA2'] += count
                elif 'wpa' in security_lower:
                    security_categories['WPA'] += count
                elif 'wep' in security_lower:
                    security_categories['WEP'] += count
                elif 'открыт' in security_lower or 'open' in security_lower:
                    security_categories['Открытые'] += count
                else:
                    security_categories['Неизвестно'] += count

            categories = list(security_categories.keys())
            values = list(security_categories.values())

            bars = ax3_2.bar(categories, values, color=['green', 'lightgreen',
                                                       'yellow', 'orange', 'red', 'gray'])
            ax3_2.set_xlabel('Категория безопасности')
            ax3_2.set_ylabel('Количество сетей')
            ax3_2.set_title('Уровень безопасности сетей')
            ax3_2.grid(True, alpha=0.3)

            # Добавляем значения на столбцы
            for bar, val in zip(bars, values):
                height = bar.get_height()
                ax3_2.text(bar.get_x() + bar.get_width()/2., height,
                          f'{val}', ha='center', va='bottom')

            plt.setp(ax3_2.get_xticklabels(), rotation=45, ha='right')
            plt.tight_layout()
            canvas3 = FigureCanvasTkAgg(fig3, master=security_frame)
            canvas3.draw()
            canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Кнопка сохранения
        def save_all_graphs():
            save_dir = filedialog.askdirectory(title="Выберите папку для сохранения графиков")
            if save_dir:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

                    if 'fig1' in locals():
                        fig1.savefig(f"{save_dir}/wifi_channels_{timestamp}.png",
                                    dpi=300, bbox_inches='tight')

                    if 'fig2' in locals():
                        fig2.savefig(f"{save_dir}/wifi_signals_{timestamp}.png",
                                    dpi=300, bbox_inches='tight')

                    if 'fig3' in locals():
                        fig3.savefig(f"{save_dir}/wifi_security_{timestamp}.png",
                                    dpi=300, bbox_inches='tight')

                    messagebox.showinfo("Успех", f"Графики сохранены в:\n{save_dir}")

                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось сохранить графики:\n{str(e)}")

        btn_frame = ttk.Frame(graph_window)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="💾 Сохранить все графики",
                  command=save_all_graphs).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть",
                  command=graph_window.destroy).pack(side=tk.LEFT, padx=5)

    def get_network_list(self) -> List[Dict[str, Any]]:
        """
        Получение списка обнаруженных сетей

        Returns:
            List[Dict]: Список Wi-Fi сетей
        """
        return self.current_wifi_networks.copy()

    def get_network_count(self) -> int:
        """
        Получение количества обнаруженных сетей

        Returns:
            int: Количество сетей
        """
        return len(self.current_wifi_networks)

    def clear_network_list(self):
        """Очистка списка сетей"""
        self.current_wifi_networks = []
        if self.wifi_tree:
            for item in self.wifi_tree.get_children():
                self.wifi_tree.delete(item)

        if hasattr(self, 'networks_count_label'):
            self.networks_count_label.config(text="Найдено сетей: 0")

        if hasattr(self, 'wifi_details'):
            self.wifi_details.delete('1.0', tk.END)
            self.wifi_details.insert('1.0', "Список сетей очищен")

    def get_network_by_ssid(self, ssid: str) -> Optional[Dict[str, Any]]:
        """
        Поиск сети по SSID

        Args:
            ssid: Имя сети для поиска

        Returns:
            Dict or None: Данные сети или None если не найдена
        """
        for network in self.current_wifi_networks:
            if network.get('ssid', '').lower() == ssid.lower():
                return network
        return None

    def get_network_by_bssid(self, bssid: str) -> Optional[Dict[str, Any]]:
        """
        Поиск сети по BSSID (MAC-адресу)

        Args:
            bssid: MAC-адрес для поиска

        Returns:
            Dict or None: Данные сети или None если не найдена
        """
        for network in self.current_wifi_networks:
            if network.get('bssid', '').lower() == bssid.lower():
                return network
        return None

    def get_strongest_network(self) -> Optional[Dict[str, Any]]:
        """
        Получение сети с самым сильным сигналом

        Returns:
            Dict or None: Данные сети или None если список пуст
        """
        if not self.current_wifi_networks:
            return None

        return max(self.current_wifi_networks,
                  key=lambda x: x.get('signal_strength', 0))

    def get_most_secure_network(self) -> Optional[Dict[str, Any]]:
        """
        Получение наиболее безопасной сети

        Returns:
            Dict or None: Данные сети или None если список пуст
        """
        if not self.current_wifi_networks:
            return None

        # Веса безопасности
        security_weights = {
            'wpa3': 100,
            'wpa2': 80,
            'wpa': 60,
            'wep': 20,
            'открыт': 0,
            'open': 0
        }

        def get_security_score(network):
            security = str(network.get('security', '')).lower()
            for key, weight in security_weights.items():
                if key in security:
                    return weight + network.get('signal_strength', 0) / 100
            return network.get('signal_strength', 0) / 100

        return max(self.current_wifi_networks, key=get_security_score)


# Пример использования
if __name__ == "__main__":
    # Тестовый запуск
    root = tk.Tk()
    root.title("Тест Wi-Fi Scanner")
    root.geometry("400x200")

    scanner = WiFiScanner()

    def open_scanner():
        scanner.create_scanner_window(root)

    ttk.Label(root, text="Wi-Fi Scanner Demo", font=('Arial', 14, 'bold')).pack(pady=20)
    ttk.Button(root, text="Открыть сканер Wi-Fi",
              command=open_scanner, width=20).pack(pady=10)
    ttk.Button(root, text="Сканировать (в фоне)",
              command=lambda: print(f"Найдено сетей: {len(scanner.scan_wifi())}"),
              width=20).pack(pady=10)
    ttk.Button(root, text="Выход",
              command=root.quit, width=20).pack(pady=10)

    root.mainloop()