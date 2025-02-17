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

    def init_plugins(self, plugin_dir='plugins'):
        """
        Initialize plugins from the specified directory.

        This function scans the given directory for Python files (.py),
        loads each file as a module, and executes its 'init' function if available.
        The function ensures that the directory exists, creating it if necessary.

        Args:
            plugin_dir (str): The directory containing the plugin files. Defaults to 'plugins'.
        """
        if not os.path.exists(plugin_dir):
            os.makedirs(plugin_dir)

        for plugin_file in os.listdir(plugin_dir):
            if plugin_file.endswith('.py'):
                plugin_name = plugin_file[:-3]
                plugin_path = os.path.join(plugin_dir, plugin_file)
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                plugin = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin)
                if hasattr(plugin, 'init'):
                    try:
                        plugin.init()
                    except Exception as e: # pylint: disable=broad-exception-caught
                        print(f"Error initializing plugin {plugin_name}: {e}")

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
                plugin_name = plugin_file[:-3]
                plugin = self.load_plugin(plugin_name)
                if plugin and hasattr(plugin, function_name):
                    filter_function = getattr(plugin, function_name)
                    value = filter_function(value)
        return value

    async def apply_filters_async(self, function_name, value):
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
                plugin_name = plugin_file[:-3]
                plugin = self.load_plugin(plugin_name)
                if plugin and hasattr(plugin, function_name):
                    filter_function = getattr(plugin, function_name)
                    value = await filter_function(value)
        return value
