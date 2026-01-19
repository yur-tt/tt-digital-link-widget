import gi
import requests

gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, AyatanaAppIndicator3 as AppIndicator, Gdk

API_URL = "http://localhost:8000/freq/manual"


class FloatingWidget(Gtk.Window):
    def __init__(self, parent_app):
        super().__init__(title="Digital Link Control")
        self.app = parent_app

        # Window configuration
        self.set_border_width(10)
        self.set_default_size(250, 150)
        self.set_keep_above(True)  # <--- Stay on top of everything
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)  # Doesn't show in Taskbar

        # Main Layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        # Frequency Dropdown
        vbox.add(Gtk.Label(label="Frequency (MHz):", xalign=0))
        self.freq_combo = Gtk.ComboBoxText()
        for f in self.app.frequencies:
            self.freq_combo.append_text(str(f))
        self.freq_combo.set_active(0)
        self.freq_combo.connect("changed", self.on_change)
        vbox.add(self.freq_combo)

        # Bitrate Dropdown
        vbox.add(Gtk.Label(label="Bitrate (kbps):", xalign=0))
        self.bit_combo = Gtk.ComboBoxText()
        for b in self.app.bitrates:
            self.bit_combo.append_text(str(b))
        self.bit_combo.set_active(0)
        self.bit_combo.connect("changed", self.on_change)
        vbox.add(self.bit_combo)

        # Close/Hide button
        btn_hide = Gtk.Button(label="Hide to Tray")
        btn_hide.connect("clicked", lambda w: self.hide())
        vbox.add(btn_hide)

        self.connect("delete-event", self.on_delete)
        self.show_all()

    def on_change(self, combo):
        # Update app state and send
        self.app.selected_freq = int(self.freq_combo.get_active_text())
        self.app.selected_bitrate = int(self.bit_combo.get_active_text())
        self.app.send_to_api()

    def on_delete(self, widget, event):
        self.hide()
        return True  # Prevents window from being destroyed


class TrayApp:
    def __init__(self):
        self.frequencies = [2412, 2437, 2462, 5805]
        self.bitrates = [1000, 2000, 5000, 10000]
        self.selected_freq = self.frequencies[0]
        self.selected_bitrate = self.bitrates[0]

        # Indicator setup
        self.indicator = AppIndicator.Indicator.new(
            "digital_link_float",
            "network-wireless",
            AppIndicator.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        # Menu
        menu = Gtk.Menu()
        item_show = Gtk.MenuItem(label="Show Control Panel")
        item_show.connect("activate", self.show_window)
        menu.append(item_show)

        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect("activate", Gtk.main_quit)
        menu.append(item_quit)

        menu.show_all()
        self.indicator.set_menu(menu)

        # Create (but don't necessarily show) the window
        self.win = FloatingWidget(self)

    def show_window(self, _):
        self.win.present()  # Brings to front

    def send_to_api(self):
        payload = {
            "freq": self.selected_freq,
            "bitrate": self.selected_bitrate,
            "bandwidth": 20, "mcs_index": 0, "fec_k": 0, "fec_n": 0
        }
        try:
            requests.post(API_URL, json=payload, timeout=1)
            print(f"Update Sent: {payload}")
        except:
            print("API Error")


if __name__ == "__main__":
    app = TrayApp()
    Gtk.main()