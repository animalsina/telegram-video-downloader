import os
import importlib.util


class PluginManager:
    def __init__(self, plugin_dir='plugins'):
        self.plugin_dir = plugin_dir
        self.filters = {}

    def load_plugin(self, plugin_name):
        """Carica dinamicamente un plugin da un file Python."""
        plugin_path = os.path.join(self.plugin_dir, f'{plugin_name}.py')
        if os.path.exists(plugin_path):
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)
            return plugin
        return None

    def apply_filters(self, function_name, value):
        """Applica tutte le funzioni dei plugin a un valore."""
        for plugin_file in os.listdir(self.plugin_dir):
            if plugin_file.endswith('.py'):
                plugin_name = plugin_file[:-3]  # Rimuovi l'estensione .py
                plugin = self.load_plugin(plugin_name)
                if plugin and hasattr(plugin, function_name):
                    # Se la funzione esiste nel plugin, applicala
                    filter_function = getattr(plugin, function_name)
                    value = filter_function(value)
        return value
