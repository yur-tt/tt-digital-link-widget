import json
import threading

import gi
import requests

gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, AyatanaAppIndicator3 as AppIndicator, Gdk

# Налаштування
API_URL_MANUAL = "http://localhost:8003/freq/manual"
API_URL_SETTINGS = "http://localhost:8003/freq/settings"
SETTINGS_FILE = "settings.json"


class FloatingWidget(Gtk.Window):
    def __init__(self, parent_app):
        super().__init__(title="Digital Link Control")
        self.app = parent_app

        self.set_border_width(10)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.MOUSE)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        self.btn_manual = Gtk.ToggleButton(label="Enable Manual Control")
        self.btn_manual.connect("toggled", self.on_manual_toggle)
        vbox.add(self.btn_manual)

        vbox.add(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        vbox.add(Gtk.Label(label="Frequency (MHz):", xalign=0))
        self.freq_combo = Gtk.ComboBoxText()

        sorted_freqs = sorted(self.app.channel_map.keys())
        for f in sorted_freqs:
            self.freq_combo.append_text(str(f))

        self.freq_combo.set_active(13)
        self.freq_combo.connect("changed", self.on_change)
        vbox.add(self.freq_combo)

        vbox.add(Gtk.Label(label="Bitrate (kbps):", xalign=0))
        self.bit_combo = Gtk.ComboBoxText()
        for b in self.app.bitrates:
            self.bit_combo.append_text(str(b))
        self.bit_combo.set_active(2)
        self.bit_combo.connect("changed", self.on_change)
        vbox.add(self.bit_combo)

        # btn_hide = Gtk.Button(label="Hide into Tray")
        # btn_hide.connect("clicked", lambda w: self.hide())
        # vbox.add(btn_hide)

        self.set_controls_sensitive(False)
        self.connect("delete-event", lambda w, e: self.hide_on_delete())
        self.show_all()

    def set_controls_sensitive(self, sensitive):
        self.freq_combo.set_sensitive(sensitive)
        self.bit_combo.set_sensitive(sensitive)

    def on_manual_toggle(self, button):
        mode = "manual" if button.get_active() else "disabled"
        button.set_label("Manual Mode: ACTIVE" if button.get_active() else "Enable Manual Control")
        self.set_controls_sensitive(button.get_active())
        self.app.send_settings(mode)

    def on_change(self, combo):
        if self.btn_manual.get_active():
            freq_str = self.freq_combo.get_active_text()
            bit_str = self.bit_combo.get_active_text()

            if freq_str and bit_str:
                freq_int = int(freq_str)
                channel_id = self.app.channel_map.get(freq_int)
                self.app.send_manual_params(channel_id, int(bit_str))

    def hide_on_delete(self):
        self.hide()
        return True


class TrayApp:
    def __init__(self):
        self.channel_map = {}  # {5180: 36, 5200: 40, ...}
        self.load_channels_from_json(SETTINGS_FILE)

        self.bitrates = [500, 1000, 2000, 4000]

        self.indicator = AppIndicator.Indicator.new(
            "digital_link_control",
            "network-wireless",
            AppIndicator.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        menu = Gtk.Menu()
        item_show = Gtk.MenuItem(label="Show Control Panel")
        item_show.connect("activate", lambda _: self.win.present())
        menu.append(item_show)
        menu.append(Gtk.SeparatorMenuItem())
        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect("activate", Gtk.main_quit)
        menu.append(item_quit)
        menu.show_all()
        self.indicator.set_menu(menu)

        self.win = FloatingWidget(self)

    def load_channels_from_json(self, filepath):
        """Завантажує частоти та канали з JSON файлу"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                for entry in data.get("channels", []):
                    if entry.get("supported"):
                        mhz = entry.get("frequency_mhz")
                        chn = entry.get("channel")
                        self.channel_map[mhz] = chn
        except Exception as e:
            print(f"Error loading JSON: {e}")
            self.channel_map = {5700: 140}

    def send_settings(self, mode):
        payload = {"mode": mode}
        threading.Thread(target=self._post, args=(API_URL_SETTINGS, payload), daemon=True).start()

    def send_manual_params(self, channel, bitrate):
        """Надсилаємо номер КАНАЛУ (freq), а не MHz"""
        payload = {
            "freq": channel,
            "bitrate": bitrate,
            "bandwidth": 20, "mcs_index": 0, "fec_k": 0, "fec_n": 0
        }
        threading.Thread(target=self._post, args=(API_URL_MANUAL, payload), daemon=True).start()

    def _post(self, url, data):
        try:
            r = requests.post(url, json=data, timeout=1.5)
            print(f"Sent to {url}: {data} | Response: {r.status_code}")
        except:
            pass


if __name__ == "__main__":
    app = TrayApp()
    Gtk.main()