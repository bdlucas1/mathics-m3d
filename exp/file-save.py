import panel as pn
import os

pn.extension()

# 1. Widget for selecting a directory
# The FileSelector allows browsing the server's filesystem.
# We configure it to select only directories.
directory_selector = pn.widgets.FileSelector(directory='~', name='Select Directory')
directory_selector.param.watch(lambda event: print(f"Selected dir: {event.new}"), 'value')

# 2. Widget for entering the new file name
file_name_input = pn.widgets.TextInput(name='File Name', placeholder='Enter file name (e.g., data.csv)')

# 3. Button to trigger the save action
save_button = pn.widgets.Button(name='Save File', button_type='success')

# 4. An output pane to display status messages
status_output = pn.indicators.LoadingSpinner(value=False, name="Saving...", align='center')

def on_save_click(event):
    """Callback function to handle the file saving logic."""
    status_output.value = True
    selected_dir_list = directory_selector.value
    if not selected_dir_list:
        status_output.name = "Error: Please select a directory"
        status_output.value = False
        return
        
    selected_dir = selected_dir_list[0] # FileSelector returns a list
    file_name = file_name_input.value
    
    if not file_name:
        status_output.name = "Error: Please enter a file name"
        status_output.value = False
        return

    full_path = os.path.join(selected_dir, file_name)
    
    # Placeholder for your actual file saving logic
    try:
        # Example: saving a simple string
        with open(full_path, 'w') as f:
            f.write("Your data goes here.")
        
        status_output.name = f"Success: File saved to {full_path}"
        # print(f"File successfully saved to {full_path}")
    except Exception as e:
        status_output.name = f"Error: Failed to save file - {e}"
        # print(f"Failed to save file: {e}")
    finally:
        status_output.value = False
    

# Link the button click to the save function
save_button.on_click(on_save_click)

# Combine widgets into a Panel layout (e.g., a Column)
save_dialog_layout = pn.Column(
    directory_selector,
    file_name_input,
    save_button,
    status_output,
    sizing_mode="stretch_width"
)

#save_dialog_layout.servable()
print("xxx hi")
save_dialog_layout.servable()
