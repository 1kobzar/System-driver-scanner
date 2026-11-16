import json as _json, re as _re
_orig_loads = _json.loads
def _clean_loads(s, *a, **kw):
    if isinstance(s, str):
        s = _re.sub(r'\?{3,}', 'Microsoft', s)
        s = _re.sub(r'(?:Microsoft)+\??', 'Microsoft', s)
    return _orig_loads(s, *a, **kw)
_json.loads = _clean_loads
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import threading
import subprocess
import webbrowser
from datetime import datetime, timedelta
import re
import json
import ctypes
import sys
import time
import base64
import os
import shutil

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def is_admin():
    """Проверка прав администратора"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def restart_as_admin():
    """Перезапустить программу от имени администратора"""
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось перезапустить: {e}")

def create_desktop_shortcut():
    """Создать ярлык на Рабочем столе, если запущен как .exe"""
    if not getattr(sys, 'frozen', False):
        return

    try:
        desktop = os.path.expandvars(r'%USERPROFILE%\Desktop')
        shortcut_path = os.path.join(desktop, 'DriverScanner Pro.lnk')

        if os.path.exists(shortcut_path):
            return

        exe_path = sys.executable
        work_dir = os.path.dirname(exe_path)

        vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{exe_path}"
oLink.WorkingDirectory = "{work_dir}"
oLink.Description = "DriverScanner Pro - Сканер ПК и драйверов"
oLink.IconLocation = "{exe_path},0"
oLink.Save
'''

        vbs_path = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'create_shortcut.vbs')
        with open(vbs_path, 'w', encoding='utf-8') as f:
            f.write(vbs_script)

        subprocess.run(['cscript.exe', vbs_path], capture_output=True, timeout=5)

        try:
            os.remove(vbs_path)
        except:
            pass
    except:
        pass

def encode_powershell_command(script):
    """Кодировать PowerShell скрипт в base64 для -EncodedCommand"""
    script_bytes = script.encode('utf-16le')
    encoded = base64.b64encode(script_bytes).decode('ascii')
    return encoded

# Единый PowerShell-скрипт для быстрого сканирования
FAST_SCAN_SCRIPT = r'''
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'SilentlyContinue'

$result = @{
    os = @{}
    cpu = @{}
    memory = @{}
    motherboard = @{}
    notebook = @{}
    gpu = @()
    network = @()
    drives = @()
    drivers = @()
    packages = @{}
}

# ОС
try {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    $result.os = @{
        name = [string]($os.Caption -replace '[^\x20-\x7E]', '?')
        version = [string]$os.Version
        build = [string]$os.BuildNumber
        arch = [string]$os.OSArchitecture
    }
} catch { }

# CPU
try {
    $cpu = Get-CimInstance Win32_Processor -ErrorAction Stop | Select-Object -First 1
    $result.cpu = @{
        name = [string]($cpu.Name.Trim() -replace '[^\x20-\x7E]', '?')
        cores = [int]($cpu.NumberOfCores)
        threads = [int]($cpu.NumberOfLogicalProcessors)
        frequency = [int]($cpu.MaxClockSpeed)
    }
} catch { }

# RAM
try {
    $mem = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
    $memModules = @(Get-CimInstance Win32_PhysicalMemory -ErrorAction Stop)
    $result.memory = @{
        total_gb = [int]($mem.TotalPhysicalMemory / 1GB)
        modules = [int]$memModules.Count
        frequency = if ($memModules.Count -gt 0) { [int]($memModules[0].Speed) } else { 0 }
    }
} catch { }

# Материнская плата
try {
    $mb = Get-CimInstance Win32_BaseBoard -ErrorAction Stop | Select-Object -First 1
    $result.motherboard = @{
        manufacturer = [string]($mb.Manufacturer -replace '[^\x20-\x7E]', '?' -replace '^\s+|\s+$', '')
        model = [string]($mb.Product -replace '[^\x20-\x7E]', '?' -replace '^\s+|\s+$', '')
        version = [string]($mb.Version -replace '[^\x20-\x7E]', '?' -replace '^\s+|\s+$', '')
    }
} catch { }

# Модель ноутбука
try {
    $comp = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
    $result.notebook = @{
        manufacturer = [string]($comp.Manufacturer -replace '[^\x20-\x7E]', '?')
        model = [string]($comp.Model -replace '[^\x20-\x7E]', '?')
    }
} catch { }

# GPU
try {
    $result.gpu = @(Get-CimInstance Win32_VideoController -ErrorAction Stop | Where-Object { $_.Name -notlike '*Microsoft*' } | ForEach-Object {
        @{
            name = [string]($_.Name -replace '[^\x20-\x7E]', '?')
            driver_version = [string]($_.DriverVersion -replace '[^\x20-\x7E]', '?')
        }
    })
} catch { }

# Накопители
try {
    $result.drives = @(Get-CimInstance Win32_DiskDrive -ErrorAction Stop | ForEach-Object {
        $size_gb = [int]($_.Size / 1GB)
        $type = if ($_.Model -like '*SSD*') { 'SSD' } else { 'HDD' }
        @{
            name = [string]($_.Model -replace '[^\x20-\x7E]', '?')
            size_gb = $size_gb
            type = $type
        }
    })
} catch { }

# Сетевые адаптеры
try {
    $result.network = @(Get-CimInstance Win32_NetworkAdapterConfiguration -ErrorAction Stop | Where-Object { $_.Description -and $_.Description -notlike '*Hyper-V*' } | Select-Object -First 10 | ForEach-Object {
        @{
            name = [string]($_.Description -replace '[^\x20-\x7E]', '?')
            status = if ($_.IPEnabled) { 'Активна' } else { 'Отключена' }
        }
    })
} catch { }

# Быстрое получение драйверов
try {
    $drivers = @{}
    Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Control\Class' -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $driverName = $_.GetValue('DriverDesc')
            $driverDate = $_.GetValue('DriverDate')
            $driverVersion = $_.GetValue('DriverVersion')

            if ($driverName -and $driverName -notlike '*Microsoft*') {
                $key = "$driverName|$driverVersion"
                if (-not $drivers.ContainsKey($key)) {
                    $drivers[$key] = @{
                        name = [string]($driverName -replace '[^\x20-\x7E]', '?')
                        version = [string]($driverVersion -replace '[^\x20-\x7E]', '?')
                        date = [string](if ($driverDate) { $driverDate } else { 'N/A' })
                        status = 'ok'
                    }
                }
            }
        } catch { }
    }
    $result.drivers = @($drivers.Values | Sort-Object -Property name)
} catch { }

# Проверка пакетов из реестра
try {
    $result.packages = @{
        vcredist = @{ installed = (Test-Path 'HKLM:\SOFTWARE\Classes\Installer\Products'); name = 'Visual C++' }
        dotnet = @{ installed = (Test-Path 'HKLM:\SOFTWARE\dotnet\Setup\InstalledVersions'); name = '.NET' }
        directx = @{ installed = (Test-Path 'HKLM:\SOFTWARE\Microsoft\DirectX'); name = 'DirectX' }
    }
} catch { }

ConvertTo-Json -InputObject $result -Depth 5 -Compress
'''

class PCScanner:
    def __init__(self):
        self.cached_data = None
        self.cache_time = None
        self.internet_available = self.check_internet()

    def check_internet(self):
        """Проверка доступности интернета"""
        try:
            result = subprocess.run(
                'powershell -Command "Test-NetConnection -ComputerName 8.8.8.8 -InformationLevel Quiet"',
                capture_output=True, text=True, timeout=5
            )
            return "True" in result.stdout
        except:
            return False

    def fast_scan(self):
        """Быстрое сканирование ПК (1-2 секунды)"""
        try:
            encoded_script = encode_powershell_command(FAST_SCAN_SCRIPT)

            result = subprocess.run(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', encoded_script],
                capture_output=True, timeout=30, encoding='utf-8', errors='replace'
            )

            if result.returncode == 0 and result.stdout.strip():
                try:
                    data = json.loads(result.stdout.strip())
                    self.cached_data = data
                    self.cache_time = datetime.now()
                    return True, data, None
                except json.JSONDecodeError as je:
                    error_msg = f"JSON парсинг ошибка: {str(je)[:100]}"
                    print(error_msg)
                    return False, None, error_msg
            else:
                error_msg = result.stderr.strip() if result.stderr else f"PowerShell код {result.returncode}"
                print(f"PowerShell ошибка: {error_msg[:200]}")
                return False, None, error_msg
        except subprocess.TimeoutExpired:
            error_msg = "Время ожидания сканирования истекло (30 сек)"
            print(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = str(e)
            print(f"Ошибка сканирования: {error_msg}")
            return False, None, error_msg

    def get_cached_data(self):
        """Получить кэшированные данные"""
        if self.cached_data and self.cache_time:
            age = (datetime.now() - self.cache_time).total_seconds()
            if age < 300:  # кэш на 5 минут
                return self.cached_data
        return None

    def clean_device_name(self, name):
        """Очистка названия устройства от мусора"""
        if not name:
            return "Unknown"

        remove_patterns = [
            r'Technology Co\., Ltd\.', r'ASUSTeK COMPUTER INC\.', r'Micro-Star International Co\., Ltd\.',
            r'Intel\(R\)', r'NVIDIA ', r'Advanced Micro Devices', r'Realtek', r'Broadcom', r'Qualcomm'
        ]

        cleaned = name
        for pattern in remove_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned if cleaned else name

    def get_unique_drivers(self, drivers_list):
        """Получить уникальные драйверы без дубликатов"""
        seen = {}
        for driver in drivers_list:
            key = (driver.get('name', 'Unknown'), driver.get('version', 'N/A'))
            if key not in seen:
                seen[key] = {'count': 1, 'driver': driver}
            else:
                seen[key]['count'] += 1

        result = []
        for (name, version), data in seen.items():
            driver = data['driver'].copy()
            if data['count'] > 1:
                driver['display_name'] = f"{name} (x{data['count']})"
            else:
                driver['display_name'] = name
            result.append(driver)

        return result

    def get_driver_status(self, driver_date, driver_name=""):
        """Определить статус драйвера"""
        if not driver_date or driver_date == 'N/A':
            return 'info', 'Информация не найдена'

        if '2006' in str(driver_date) and '06' in str(driver_date):
            return 'ok', 'Системный драйвер'

        try:
            date_obj = datetime.strptime(str(driver_date)[:8], "%Y%m%d")
            age_days = (datetime.now() - date_obj).days

            if age_days > 540:
                return 'warning', f'Устарел ({age_days} дней)'
            else:
                return 'ok', f'Актуален ({age_days} дней)'
        except:
            return 'info', 'Информация не найдена'

    def get_driver_urls(self, manufacturer, model, device_type='motherboard'):
        """Получить URL для скачивания драйверов"""
        manufacturer_lower = (manufacturer or "").lower()

        if device_type == 'motherboard':
            if 'msi' in manufacturer_lower:
                return 'https://msi.com'
            elif 'gigabyte' in manufacturer_lower:
                return 'https://gigabyte.com'
            elif 'asus' in manufacturer_lower:
                return 'https://asus.com'
            elif 'asrock' in manufacturer_lower:
                return 'https://asrock.com'
            else:
                return f'https://yandex.ru/search/?text={manufacturer}'
        elif device_type == 'gpu':
            if 'nvidia' in manufacturer_lower:
                return 'https://nvidia.com'
            elif 'amd' in manufacturer_lower:
                return 'https://amd.com'
            elif 'intel' in manufacturer_lower:
                return 'https://intel.com'
        return 'https://yandex.ru'


class ScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DriverScanner Pro - Сканер ПК и драйверов")
        self.root.geometry("1600x900")
        self.root.minsize(1200, 700)
        self.scanner = PCScanner()
        self.show_all_drivers = True
        self.is_admin = is_admin()
        self.is_scanning = False
        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        if not self.is_admin:
            admin_frame = ctk.CTkFrame(self.root, fg_color="#ffc107", corner_radius=0)
            admin_frame.pack(side="top", fill="x", padx=0, pady=0)

            admin_label = ctk.CTkLabel(
                admin_frame,
                text="⚠️ Запущено без прав администратора",
                text_color="black",
                font=("Arial", 11, "bold")
            )
            admin_label.pack(side="left", padx=10, pady=8)

            admin_btn = ctk.CTkButton(
                admin_frame,
                text="Перезапустить от имени администратора",
                command=restart_as_admin,
                fg_color="#ff9800",
                text_color="white",
                hover_color="#e65100",
                height=25
            )
            admin_btn.pack(side="right", padx=10, pady=8)

        top_frame = ctk.CTkFrame(self.root, fg_color="#1e1e1e")
        top_frame.pack(side="top", fill="x", padx=10, pady=10)

        self.scan_btn = ctk.CTkButton(
            top_frame,
            text="🔍 Сканировать ПК",
            command=self.scan_pc,
            fg_color="#1f6aa5",
            hover_color="#0d47a1"
        )
        self.scan_btn.pack(side="left", padx=5)

        self.check_updates_btn = ctk.CTkButton(
            top_frame,
            text="⚡ Проверить обновления",
            command=self.check_driver_updates,
            fg_color="#7c3b2b",
            hover_color="#a85a3a"
        )
        self.check_updates_btn.pack(side="left", padx=5)

        self.report_btn = ctk.CTkButton(
            top_frame,
            text="📄 Сохранить отчёт",
            command=self.save_report,
            fg_color="#555555",
            hover_color="#777777"
        )
        self.report_btn.pack(side="left", padx=5)

        self.status_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        self.status_frame.pack(side="left", padx=30, fill="x", expand=True)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Готово к сканированию",
            text_color="gray"
        )
        self.status_label.pack(side="left")

        self.summary_label = ctk.CTkLabel(
            self.status_frame,
            text="",
            text_color="#90caf9"
        )
        self.summary_label.pack(side="left", padx=20)

        self.progress_bar = ctk.CTkProgressBar(self.root, height=4)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=0, pady=0)

        content_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        content_frame.grid_columnconfigure(0, weight=4)
        content_frame.grid_columnconfigure(1, weight=6)

        left_label = ctk.CTkLabel(
            content_frame,
            text="🖥️ Конфигурация и параметры ПК",
            font=("Arial", 14, "bold"),
            text_color="#64b5f6"
        )
        left_label.grid(row=0, column=0, sticky="ew", padx=5, pady=(0, 5))

        self.left_frame = ctk.CTkScrollableFrame(content_frame, fg_color="#1a1a1a")
        self.left_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        right_header_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        right_header_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=(0, 5))

        right_label = ctk.CTkLabel(
            right_header_frame,
            text="⚙️ Драйверы и неустановленное ПО",
            font=("Arial", 14, "bold"),
            text_color="#64b5f6"
        )
        right_label.pack(side="left")

        self.filter_switch = ctk.CTkSwitch(
            right_header_frame,
            text="Только проблемы",
            command=self.toggle_filter,
            onvalue=True,
            offvalue=False
        )
        self.filter_switch.pack(side="right", padx=10)

        self.right_frame = ctk.CTkScrollableFrame(content_frame, fg_color="#1a1a1a")
        self.right_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        content_frame.grid_rowconfigure(1, weight=1)

    def update_progress(self, value):
        """Обновить прогресс-бар"""
        if value >= 1.0:
            self.progress_bar.set(0)
        else:
            self.progress_bar.set(value)

    def toggle_filter(self):
        """Переключить фильтр"""
        self.show_all_drivers = not self.filter_switch.get()
        data = self.scanner.get_cached_data()
        if data:
            self.display_drivers(data)

    def scan_pc(self):
        """Быстрое сканирование ПК"""
        if self.is_scanning:
            return

        self.is_scanning = True
        self.status_label.configure(text="⏳ Сканирование...")
        self.update_progress(0.5)
        self.scan_btn.configure(state="disabled")

        thread = threading.Thread(target=self._scan_thread, daemon=True)
        thread.start()

    def _scan_thread(self):
        """Поток сканирования"""
        try:
            success, data, error = self.scanner.fast_scan()
            if success:
                self.root.after(0, lambda: self.display_system_info(data))
                self.root.after(0, lambda: self.display_drivers(data))
                self.root.after(0, lambda: self.update_summary(data))
                self.root.after(0, lambda: self.status_label.configure(text="✅ Сканирование завершено"))
            else:
                error_text = error if error else "Неизвестная ошибка"
                self.root.after(0, lambda: messagebox.showerror("Ошибка сканирования", f"Не удалось отсканировать систему:\n{error_text}"))
                self.root.after(0, lambda: self.status_label.configure(text="❌ Ошибка"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Критическая ошибка: {str(e)[:200]}"))
        finally:
            self.root.after(0, lambda: self.update_progress(0))
            self.root.after(0, lambda: self.scan_btn.configure(state="normal"))
            self.is_scanning = False

    def display_system_info(self, data):
        """Отображение информации о системе"""
        for widget in self.left_frame.winfo_children():
            widget.destroy()

        if not data:
            self._add_section(self.left_frame, "Ошибка")
            self._add_info_item(self.left_frame, "Нет данных для отображения", "#f44336")
            return

        # Модель ноутбука
        if data.get('notebook', {}).get('manufacturer'):
            self._add_section(self.left_frame, "💻 Модель устройства")
            self._add_info_item(self.left_frame, f"{data['notebook']['manufacturer']} {data['notebook']['model']}", "#64b5f6")

        # ОС
        if data.get('os'):
            self._add_section(self.left_frame, "📀 Операционная система")
            os_info = data['os']
            os_name = os_info.get('name', 'N/A').replace('Microsoft', 'Microsoft')
            self._add_info_item(
                self.left_frame,
                f"{os_name}\nВерсия: {os_info.get('version', 'N/A')}\nСборка: {os_info.get('build', 'N/A')}"
            )

        # CPU
        if data.get('cpu'):
            self._add_section(self.left_frame, "💻 Процессор (CPU)")
            cpu = data['cpu']
            freq_ghz = round(cpu.get('frequency', 0) / 1000, 2) if cpu.get('frequency') else 'N/A'
            self._add_info_item(
                self.left_frame,
                f"{cpu.get('name', 'N/A')}\nЯдер: {cpu.get('cores', '?')}, Потоков: {cpu.get('threads', '?')}\nЧастота: {freq_ghz} ГГц"
            )

        # RAM
        if data.get('memory'):
            self._add_section(self.left_frame, "🧠 Оперативная память (RAM)")
            mem = data['memory']
            self._add_info_item(
                self.left_frame,
                f"Объём: {mem.get('total_gb', 'N/A')} ГБ\nМодулей: {mem.get('modules', 'N/A')}\nЧастота: {mem.get('frequency', 'N/A')} МГц"
            )

        # Материнская плата
        if data.get('motherboard'):
            self._add_section(self.left_frame, "🔌 Материнская плата")
            mb = data['motherboard']
            frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
            frame.pack(fill="x", padx=10, pady=5)

            info_text = f"{mb.get('manufacturer', 'N/A')} {mb.get('model', 'N/A')}"
            info_label = ctk.CTkLabel(frame, text=info_text, text_color="white", justify="left")
            info_label.pack(side="left", padx=5, fill="x", expand=True)

            url = self.scanner.get_driver_urls(mb.get('manufacturer', ''), mb.get('model', ''), device_type='motherboard')
            dl_btn = ctk.CTkButton(
                frame,
                text="📥 Скачать",
                width=100,
                command=lambda u=url: webbrowser.open(u)
            )
            dl_btn.pack(side="right", padx=5)

        # GPU
        if data.get('gpu'):
            self._add_section(self.left_frame, "🎮 Видеокарта (GPU)")
            for gpu in data['gpu'][:2]:
                frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
                frame.pack(fill="x", padx=10, pady=5)

                info_label = ctk.CTkLabel(frame, text=f"{gpu.get('name', 'N/A')}\nДрайвер: {gpu.get('driver_version', 'N/A')}", text_color="white", justify="left")
                info_label.pack(side="left", padx=5, fill="x", expand=True)

                url = self.scanner.get_driver_urls(gpu.get('name', ''), "", device_type='gpu')
                dl_btn = ctk.CTkButton(
                    frame,
                    text="📥 Скачать",
                    width=100,
                    command=lambda u=url: webbrowser.open(u)
                )
                dl_btn.pack(side="right", padx=5)

        # Накопители
        if data.get('drives'):
            self._add_section(self.left_frame, "💾 Накопители (HDD/SSD)")
            for drive in data['drives']:
                self._add_info_item(self.left_frame, f"{drive.get('name', 'N/A')}\nОбъём: {drive.get('size_gb', 'N/A')} ГБ ({drive.get('type', 'N/A')})")

        # Сеть
        if data.get('network'):
            self._add_section(self.left_frame, "🌐 Сетевые адаптеры")
            for adapter in data['network'][:3]:
                self._add_info_item(self.left_frame, f"{adapter.get('name', 'N/A')}\nСтатус: {adapter.get('status', 'N/A')}")

    def display_drivers(self, data):
        """Отображение информации о драйверах"""
        for widget in self.right_frame.winfo_children():
            widget.destroy()

        if not data:
            self._add_section(self.right_frame, "Ошибка")
            self._add_info_item(self.right_frame, "Нет данных для отображения", "#f44336")
            return

        # Неустановленные пакеты
        self._add_section(self.right_frame, "📦 Неустановленное ПО")
        missing_count = 0
        for key, pkg in data.get('packages', {}).items():
            if not pkg.get('installed', False):
                missing_count += 1
                frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
                frame.pack(fill="x", padx=10, pady=5)

                label = ctk.CTkLabel(frame, text="❌", text_color="#f44336", font=("Arial", 12))
                label.pack(side="left", padx=5)

                info = ctk.CTkLabel(frame, text=f"{pkg.get('name', 'N/A')}\nНе установлено", text_color="#f44336", justify="left")
                info.pack(side="left", padx=5, fill="x", expand=True)

        if missing_count == 0:
            self._add_info_item(self.right_frame, "✅ Все пакеты установлены", color="#4caf50")

        # Все драйверы (всегда показываем, но фильтруем по статусу если нужно)
        self._add_section(self.right_frame, "📋 Все установленные драйверы")
        unique_drivers = self.scanner.get_unique_drivers(data.get('drivers', []))

        if self.show_all_drivers:
            # Показываем только проблемные драйверы
            displayed = 0
            for driver in unique_drivers:
                status_type, status_text = self.scanner.get_driver_status(driver.get('date', 'N/A'), driver.get('name', ''))
                if status_type in ['warning', 'error']:
                    self._add_driver_item(self.right_frame, driver.get('display_name', 'Unknown'), f"Версия: {driver.get('version', 'N/A')}\n{status_text}", status_type)
                    displayed += 1
                    if displayed >= 20:
                        break
            if displayed == 0:
                self._add_info_item(self.right_frame, "✅ Проблемных драйверов не найдено", color="#4caf50")
        else:
            # Показываем все драйверы
            for driver in unique_drivers[:30]:
                status_type, status_text = self.scanner.get_driver_status(driver.get('date', 'N/A'), driver.get('name', ''))
                self._add_driver_item(self.right_frame, driver.get('display_name', 'Unknown'), f"Версия: {driver.get('version', 'N/A')}\n{status_text}", status_type)

    def _add_section(self, parent, title):
        """Добавление заголовка секции"""
        section = ctk.CTkLabel(parent, text=title, font=("Arial", 12, "bold"), text_color="#64b5f6")
        section.pack(anchor="w", padx=10, pady=(10, 5))

    def _add_info_item(self, parent, text, color="white"):
        """Добавление информационного элемента"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=5)

        label = ctk.CTkLabel(frame, text=text, text_color=color, justify="left")
        label.pack(anchor="w")

    def _add_driver_item(self, parent, name, info, status):
        """Добавление элемента драйвера"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=5)

        color_map = {'ok': '#4caf50', 'warning': '#ffc107', 'error': '#f44336', 'info': '#90caf9'}
        emoji_map = {'ok': '✅', 'warning': '⚠️', 'error': '❌', 'info': 'ℹ️'}

        emoji_label = ctk.CTkLabel(frame, text=emoji_map.get(status, 'ℹ️'), font=("Arial", 10))
        emoji_label.pack(side="left", padx=5)

        info_label = ctk.CTkLabel(frame, text=f"{name}\n{info}", text_color=color_map.get(status, 'white'), justify="left", font=("Arial", 9))
        info_label.pack(side="left", padx=5, fill="x", expand=True)

    def update_summary(self, data):
        """Обновить сводку статуса"""
        total_devices = len(data.get('gpu', [])) + len(data.get('network', []))
        outdated = sum(1 for d in data.get('drivers', []) if self.scanner.get_driver_status(d.get('date', 'N/A'), d.get('name', ''))[0] == 'warning')
        internet_status = "✓ Интернет" if self.scanner.internet_available else "✗ Без интернета"
        self.summary_label.configure(text=f"Устройств: {total_devices} | Устарелых: {outdated} | {internet_status}")

    def check_driver_updates(self):
        """Проверка обновлений драйверов"""
        data = self.scanner.get_cached_data()
        if not data:
            if not self.is_scanning:
                self.status_label.configure(text="⏳ Сканирование перед проверкой...")
                thread = threading.Thread(target=self._scan_and_check, daemon=True)
                thread.start()
            return

        self._show_updates_window(data)

    def _scan_and_check(self):
        """Сканирование и проверка обновлений"""
        try:
            success, data, error = self.scanner.fast_scan()
            if success:
                self.root.after(0, lambda: self._show_updates_window(data))
            else:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка сканирования:\n{error}"))
        finally:
            self.root.after(0, lambda: self.update_progress(0))

    def _show_updates_window(self, data):
        """Показать окно обновлений"""
        problematic_drivers = []
        for driver in data.get('drivers', []):
            status_type, status_text = self.scanner.get_driver_status(driver.get('date', 'N/A'), driver.get('name', ''))
            if status_type in ['warning', 'error']:
                driver_copy = driver.copy()
                driver_copy['problem_type'] = status_type
                driver_copy['problem_text'] = status_text
                problematic_drivers.append(driver_copy)

        unique_drivers = self.scanner.get_unique_drivers(problematic_drivers)

        if not unique_drivers:
            messagebox.showinfo("Информация", "✅ Нет проблемных драйверов!")
            return

        UpdateWindow(self.root, unique_drivers, self.scanner, self.is_admin)

    def save_report(self):
        """Сохранение отчёта в HTML"""
        data = self.scanner.get_cached_data()
        if not data:
            messagebox.showwarning("Предупреждение", "Сначала выполните сканирование ПК")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML файлы", "*.html"), ("Все файлы", "*.*")],
            initialfile=f"DriverScanner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )

        if file_path:
            html = f"""<html><head><meta charset="UTF-8"><title>DriverScanner Report</title>
<style>body {{ font-family: Arial; background: #1e1e1e; color: #fff; padding: 20px; }}
h1 {{ color: #64b5f6; }} h2 {{ color: #81c784; }}
.section {{ background: #2d2d2d; padding: 15px; margin: 10px 0; border-radius: 5px; }}</style></head><body>
<h1>📊 Отчёт DriverScanner Pro</h1><p>Дата: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
<h2>🖥️ Система</h2><div class="section">
<p><strong>ОС:</strong> {data.get('os', {}).get('name', 'N/A')} (сборка {data.get('os', {}).get('build', 'N/A')})</p>
<p><strong>CPU:</strong> {data.get('cpu', {}).get('name', 'N/A')}</p>
<p><strong>RAM:</strong> {data.get('memory', {}).get('total_gb', 'N/A')} ГБ</p>
</div></body></html>"""

            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                messagebox.showinfo("Успех", f"Отчёт сохранён в:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка сохранения отчёта:\n{str(e)[:200]}")


class UpdateWindow(ctk.CTkToplevel):
    def __init__(self, parent, drivers, scanner, is_admin):
        super().__init__(parent)
        self.title("⚡ Проверка обновлений")
        self.geometry("700x400")
        self.minsize(600, 300)
        self.drivers = drivers

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=10)

        title_label = ctk.CTkLabel(header_frame, text="📊 Требуют обновления", font=("Arial", 14, "bold"), text_color="#ff9800")
        title_label.pack(anchor="w")

        count_label = ctk.CTkLabel(header_frame, text=f"Найдено {len(drivers)} устройств", text_color="gray")
        count_label.pack(anchor="w")

        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        for driver in drivers[:15]:
            card = ctk.CTkFrame(scroll_frame, fg_color="#2d2d2d")
            card.pack(fill="x", padx=0, pady=4)

            label = ctk.CTkLabel(card, text='⚠️' if driver.get('problem_type') == 'warning' else '❌', font=("Arial", 12))
            label.pack(side="left", padx=10, pady=5)

            info = ctk.CTkLabel(card, text=f"{driver.get('display_name', 'N/A')}\n{driver.get('problem_text', '')}", text_color="#ffc107", justify="left", font=("Arial", 9))
            info.pack(side="left", padx=5, pady=5, fill="x", expand=True)

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=10)

        close_btn = ctk.CTkButton(button_frame, text="✖ Закрыть", command=self.destroy, fg_color="#555555")
        close_btn.pack(side="right", padx=5)


if __name__ == "__main__":
    create_desktop_shortcut()
    root = ctk.CTk()
    app = ScannerApp(root)
    print("✅ DriverScanner Pro запущен")
    root.mainloop()


