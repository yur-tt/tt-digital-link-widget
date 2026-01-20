import json
import os
import threading

import gi
import requests

from settings import API_URL_SETTINGS, API_URL_MANUAL, SETTINGS_FILE

gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, AyatanaAppIndicator3 as AppIndicator, Gdk, GLib


class FloatingWidget(Gtk.Window):
    def __init__(self, parent_app):
        super().__init__(title="Перемикання відео")
        self.app = parent_app
        self.expanded = False

        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_resizable(False)
        self.set_border_width(1)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(self.main_box)

        self.btn_manual = Gtk.ToggleButton(label="Увімкнути")
        self.btn_manual.connect("toggled", self.on_manual_toggle)
        self.main_box.add(self.btn_manual)

        self.btn_expand = Gtk.Button(label="Розгорнути ⬇")
        self.btn_expand.connect("clicked", self.toggle_expand)
        self.main_box.add(self.btn_expand)

        self.main_box.add(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        self.collapsed_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.collapsed_box.add(Gtk.Label(label="Частота:", xalign=0))
        self.freq_combo = Gtk.ComboBoxText()
        self.collapsed_box.add(self.freq_combo)
        self.main_box.add(self.collapsed_box)

        self.expanded_scroll = Gtk.ScrolledWindow()
        self.expanded_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.expanded_scroll.set_min_content_height(750)

        self.freq_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.expanded_scroll.add(self.freq_list_box)
        self.main_box.add(self.expanded_scroll)

        self.main_box.add(Gtk.Label(label="Бітрейт (kbps):", xalign=0))
        self.bit_combo = Gtk.ComboBoxText()
        for b in self.app.bitrates:
            self.bit_combo.append_text(str(b))
        self.bit_combo.set_active(2)
        self.bit_combo.connect("changed", self.on_bitrate_change)
        self.main_box.add(self.bit_combo)

        # Кнопка приховати у трей
        # btn_hide = Gtk.Button(label="Hide into Tray")
        # btn_hide.connect("clicked", lambda w: self.hide())
        # self.main_box.add(btn_hide)

        self.setup_frequencies()
        self.set_controls_sensitive(False)

        self.connect("delete-event", self.on_delete)

        self.show_all()
        self.expanded_scroll.hide()
        self.update_view()

    def setup_frequencies(self):
        sorted_freqs = sorted(self.app.channel_map.keys())
        first_radio = None

        for f in sorted_freqs:
            self.freq_combo.append_text(str(f))

            btn = Gtk.RadioButton.new_with_label_from_widget(first_radio, f"{f} MHz")
            if not first_radio:
                first_radio = btn
            btn.set_mode(False)
            btn.connect("toggled", self.on_freq_btn_toggled, f)
            self.freq_list_box.add(btn)

        self.freq_combo.set_active(13)
        self.freq_combo.connect("changed", self.on_combo_change)

    def update_view(self):
        display = self.get_display()
        window = self.get_window()

        if window:
            monitor = display.get_monitor_at_window(window)
        else:
            monitor = display.get_monitor(0)
        geo = monitor.get_geometry()

        if self.expanded:
            self.collapsed_box.hide()
            self.expanded_scroll.show()
            self.btn_expand.set_label("Згорнути ⬆")
            self.set_size_request(100, geo.height)
            self.move(geo.x, geo.y)
        else:
            self.expanded_scroll.hide()
            self.collapsed_box.show()
            self.btn_expand.set_label("Розгорнути ⬇")
            self.set_size_request(250, -1)
            self.set_position(Gtk.WindowPosition.MOUSE)

    def toggle_expand(self, btn):
        self.expanded = not self.expanded
        self.update_view()

    def set_controls_sensitive(self, sensitive):
        self.freq_combo.set_sensitive(sensitive)
        self.freq_list_box.set_sensitive(sensitive)
        self.bit_combo.set_sensitive(sensitive)

    def on_manual_toggle(self, button):
        active = button.get_active()
        self.set_controls_sensitive(active)
        button.set_label("Увімкнено" if active else "Увімкнути")
        self.app.send_settings("manual" if active else "disabled")

    def on_freq_btn_toggled(self, btn, freq_mhz):
        if btn.get_active() and self.btn_manual.get_active() and self.expanded:
            self.process_and_send(freq_mhz)

    def on_combo_change(self, combo):
        if self.btn_manual.get_active() and not self.expanded:
            text = combo.get_active_text()
            if text:
                self.process_and_send(int(text))

    def on_bitrate_change(self, combo):
        if self.btn_manual.get_active():
            freq_text = self.freq_combo.get_active_text()
            if freq_text:
                self.process_and_send(int(freq_text))

    def process_and_send(self, freq_mhz):
        bitrate = int(self.bit_combo.get_active_text() or 1000)
        channel = self.app.channel_map.get(freq_mhz)
        if channel:
            self.app.send_manual_params(channel, bitrate)

    def on_delete(self, widget, event):
        self.hide()
        return True


class TrayApp:
    def __init__(self):
        self.channel_map = {}
        self.bitrates = [500, 1000, 2000, 4000]

        self.load_channels_from_json(SETTINGS_FILE)

        self.indicator = AppIndicator.Indicator.new(
            "digital_link_widget",
            "network-wireless",
            AppIndicator.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        menu = Gtk.Menu()
        item_show = Gtk.MenuItem(label="Відкрити панель")
        item_show.connect("activate", lambda _: self.win.present())
        menu.append(item_show)

        menu.append(Gtk.SeparatorMenuItem())

        # item_quit = Gtk.MenuItem(label="Quit")
        # item_quit.connect("activate", Gtk.main_quit)
        # menu.append(item_quit)

        menu.show_all()
        self.indicator.set_menu(menu)

        self.win = FloatingWidget(self)

    def load_channels_from_json(self, filepath):
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found. Using defaults.")
            self.channel_map = {5805: 161}
            return

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                for ch in data.get("channels", []):
                    if ch.get("supported"):
                        mhz = ch.get("frequency_mhz")
                        num = ch.get("channel")
                        self.channel_map[mhz] = num
        except Exception as e:
            print(f"JSON Error: {e}")
            self.channel_map = {5700: 140}

    def send_settings(self, mode):
        payload = {"mode": mode}
        threading.Thread(target=self._post, args=(API_URL_SETTINGS, payload), daemon=True).start()

    def send_manual_params(self, channel_num, bitrate):
        payload = {
            "freq": channel_num,
            "bitrate": bitrate,
            "bandwidth": 20, "mcs_index": 0, "fec_k": 0, "fec_n": 0
        }
        threading.Thread(target=self._post, args=(API_URL_MANUAL, payload), daemon=True).start()

    def _post(self, url, data):
        try:
            requests.post(url, json=data, timeout=1.0)
            print(f"POST to {url.split('/')[-1]}: {data}")
        except Exception as e:
            print(f"Request failed: {e}")


if __name__ == "__main__":
    app = TrayApp()
    Gtk.main()