"""
Plugin Manager class.

This class is used to load and manage plugins. A plugin is a python file
in the plugin directory. Each plugin is loaded and the function with the
name that is the same as the plugin name is called. The function should
return a dictionary with the following structure:
{
    "filter_name": function,
    "filter_name_2": function_2,
    ...
}
"""
import os
import importlib.util


class PluginManager:
    """
    Plugin Manager
    """
    def __init__(self, plugin_dir='plugins'):
        self.plugin_dir = plugin_dir
        self.filters = {}

    def load_plugin(self, plugin_name):
        """
        Load a plugin by its name.

        Args:
            plugin_name (str): The name of the plugin to load.

        Returns:
            module: The loaded plugin module or None if the plugin does not exist.

        """
        plugin_path = os.path.join(self.plugin_dir, f'{plugin_name}.py')
        if os.path.exists(plugin_path):
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)
            return plugin
        return None

    def apply_filters(self, function_name, value):
        """
        Apply a sequence of filter functions from plugins to a given value.

        This method iterates through all the Python files in the plugin directory,
        loads each plugin, and checks if the specified function exists within the plugin.
        If the function is found, it is applied to the input value.

        Args:
            function_name (str): The name of the function to apply from each plugin.
            value: The initial value to be filtered by the plugin functions.

        Returns:
            The value after being processed by all applicable plugin functions.

        """
        for plugin_file in os.listdir(self.plugin_dir):
            if plugin_file.endswith('.py'):
                plugin_name = plugin_file[:-3]  # Rimuovi l'estensione .py
                plugin = self.load_plugin(plugin_name)
                if plugin and hasattr(plugin, function_name):
                    # Se la funzione esiste nel plugin, applicala
                    filter_function = getattr(plugin, function_name)
                    value = filter_function(value)
        return value
