
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy as np

class PlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.ax = self.figure.add_subplot(111)

        self.sample_names = None
        self.wavelengths_data = None
        self.spectra_data = None
        self.lines = []
        self.selected_line = None
        self.annotation = None

    def clear(self):
        self.ax.clear()
        self.canvas.draw()

    def plot_spectra(self, wavelengths, spectra, title="NIR Spectra", sample_names=None):
        self.ax.clear()
        self.lines = []
        self.wavelengths_data = wavelengths
        self.spectra_data = spectra
        self.sample_names = sample_names
        self.selected_line = None

        if self.annotation:
            self.annotation.remove()
            self.annotation = None

        if spectra.ndim == 1:
            line, = self.ax.plot(wavelengths, spectra, linewidth=1.5, picker=5)
            self.lines.append(line)
        else:
            for i in range(spectra.shape[0]):
                line, = self.ax.plot(wavelengths, spectra[i], alpha=0.7, linewidth=1, picker=5)
                self.lines.append(line)

        self.ax.set_xlabel('Wavelength (nm)', fontsize=10)
        self.ax.set_ylabel('Absorbance', fontsize=10)
        self.ax.set_title(title, fontsize=12, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        self.figure.tight_layout()

        self.canvas.mpl_connect('pick_event', self.on_pick)

        self.canvas.draw()

    def on_pick(self, event):
        if event.artist not in self.lines:
            return

        line_index = self.lines.index(event.artist)

        if self.selected_line is not None:
            self.selected_line.set_linewidth(1)
            self.selected_line.set_alpha(0.7)

        self.selected_line = event.artist
        self.selected_line.set_linewidth(3)
        self.selected_line.set_alpha(1.0)

        if self.annotation:
            self.annotation.remove()

        label = f"Sample #{line_index + 1}"
        if self.sample_names is not None and line_index < len(self.sample_names):
            label = f"Sample: {self.sample_names[line_index]}"

        x_pos = self.wavelengths_data[len(self.wavelengths_data) // 2]
        if self.spectra_data.ndim == 1:
            y_pos = self.spectra_data[len(self.spectra_data) // 2]
        else:
            y_pos = self.spectra_data[line_index][len(self.spectra_data[line_index]) // 2]

        self.annotation = self.ax.annotate(
            label,
            xy=(x_pos, y_pos),
            xytext=(20, 20),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.8),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='black'),
            fontsize=10,
            fontweight='bold'
        )

        self.canvas.draw()
