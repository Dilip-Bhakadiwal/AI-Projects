import tkinter as tk
from tkinter import messagebox
from preprocessor import clean_text, summarize_text

# Create the main window
root = tk.Tk()
root.title("Text Summarizer & Grammar Correction Tool")
root.geometry("700x600")
root.config(bg="#f0f0f0")  # Set a light background color

# Define a font style for labels and buttons
font_label = ("Helvetica", 12, "bold")
font_button = ("Helvetica", 14, "bold")
font_text = ("Helvetica", 12)

# Function to process the input and display the summarized and corrected text
def process_input():
    # Get the input text from the Text widget
    input_text = text_input.get("1.0", "end-1c")
    
    # Check if the input is empty
    if not input_text.strip():
        messagebox.showwarning("Input Error", "Please enter some text to process.")
        return
    
    # Summarize the input text
    summarized_text = summarize_text(input_text)
    
    # Correct the grammar of the summarized text
    corrected_text = clean_text(summarized_text)
    
    # Display the corrected and summarized text in the output Text widget
    text_output.delete("1.0", "end")
    text_output.insert("1.0", corrected_text)

# Create a Frame for better layout
frame = tk.Frame(root, bg="#f0f0f0")
frame.pack(padx=20, pady=20, fill="both", expand=True)

# Create the label for the input text area with customization
label_input = tk.Label(frame, text="Enter Text to Summarize and Correct:", font=font_label, bg="#f0f0f0")
label_input.pack(pady=10)

# Create the Text widget for input with customized appearance
text_input = tk.Text(frame, height=10, width=70, font=font_text, wrap="word", bd=2, relief="solid", padx=10, pady=10)
text_input.pack(pady=10)

# Create the button to process the input with improved styling
button_process = tk.Button(frame, text="Summarize and Correct", command=process_input, font=font_button, bg="#4CAF50", fg="white", bd=0, relief="solid", width=20, height=2)
button_process.pack(pady=10)

# Create the label for the output text area with customization
label_output = tk.Label(frame, text="Processed Text:", font=font_label, bg="#f0f0f0")
label_output.pack(pady=10)

# Create the Text widget for output with customized appearance
text_output = tk.Text(frame, height=10, width=70, font=font_text, wrap="word", bd=2, relief="solid", padx=10, pady=10)
text_output.pack(pady=10)

# Start the Tkinter main loop
root.mainloop()
