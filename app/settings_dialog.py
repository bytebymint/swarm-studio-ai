from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLineEdit, QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget)


class SettingsDialog(QDialog):
    def __init__(self, values, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Studio settings')
        self.resize(560, 580)
        self.fields = {}
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        groups = {
            'Animation': [('agents','Crew limit (appears as work is available)',2,12),('speed','Default speed',.5,5.),('cursor_size','Cursor scale',.5,2.),('smoothness','Movement smoothness',.4,2.),('overlay_opacity','Overlay opacity',.2,1.),('intro','Intro choreography'),('names','Agent names'),('auto_tour','Auto Tour'),('reduced_motion','Reduced motion')],
            'Capture': [('width','Viewport width',320,2560),('height','Viewport height',400,1600),('timeout','Capture timeout (seconds)',5,120),('max_elements','Maximum visual elements',100,5000),('max_height','Maximum document height',1000,40000),('max_asset_mb','Maximum asset size (MB)',1,64),('max_total_mb','Total asset budget (MB)',10,500),('page_limit','Same-origin page limit (1 = single page)',1,8),('crawl_depth','Maximum link depth',0,2),('lazy_load','Discover lazy-loaded content')],
            'Export': [('export_directory','Default export folder'),('include_screenshots','Include screenshots'),('include_blueprint','Include animation blueprint'),('open_export','Open export folder when finished')],
            'Audio': [('sound','Enable event sounds'),('volume','Volume',0.,1.),('reduced_audio','Reduce keyboard sounds')],
        }
        for title, fields in groups.items():
            widget = QWidget()
            form = QFormLayout(widget)
            form.setVerticalSpacing(18)
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(widget)
            tabs.addTab(scroll, title)
            for entry in fields:
                key,label,*bounds = entry
                value = values[key]
                if isinstance(value,bool):
                    field=QCheckBox();field.setChecked(value)
                elif isinstance(value,int):
                    field=QSpinBox();field.setRange(*bounds);field.setValue(value)
                elif isinstance(value,float):
                    field=QDoubleSpinBox();field.setRange(*bounds);field.setSingleStep(.1);field.setValue(value)
                else:
                    field=QLineEdit(value)
                field.setAccessibleName(label)
                self.fields[key]=field
                form.addRow(label,field)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        result={}
        for key,field in self.fields.items():
            result[key]=field.isChecked() if isinstance(field,QCheckBox) else field.value() if isinstance(field,(QSpinBox,QDoubleSpinBox)) else field.text()
        return result
