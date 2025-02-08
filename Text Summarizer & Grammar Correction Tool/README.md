# Text Summarizer & Grammar Correction Tool

This project is a simple GUI-based application built with Python's Tkinter library. It allows users to input text, which is then summarized and grammatically corrected using pre-trained transformer models.

## Features
- **Text Summarization:** Reduces lengthy text to concise summaries.
- **Grammar Correction:** Fixes grammatical errors in the summarized text.
- **User-Friendly Interface:** Easy-to-use GUI for seamless interaction.

## Requirements
- Python 3.x
- Install the required Python packages:
  ```bash
  pip install transformers torch tkinter
  ```

## Setup Instructions

### 1. Download Pre-trained Models

- **Summarization Model:**
  Download from [facebook/bart-large-cnn](https://huggingface.co/facebook/bart-large-cnn/tree/main).
  
- **Grammar Correction Model:**
  Download from [prithivida/grammar_error_correcter_v1](https://huggingface.co/prithivida/grammar_error_correcter_v1/tree/main).

### 2. Organize Models
Save the downloaded models in the following directory structure:

```
project/
├── app.py
├── preprocesser.py
├── model_1/  # Grammar Correction Model
└── model_2/  # Summarization Model
```

### 3. Run the Application
Navigate to the project directory and execute the following command:

```bash
python app.py
```

## Usage
1. **Enter Text:** Type or paste the text you want to process in the input box.
2. **Summarize and Correct:** Click the "Summarize and Correct" button.
3. **View Results:** The summarized and corrected text will appear in the output box.

## File Descriptions
- **app.py:** Contains the Tkinter GUI code to handle user interactions.
- **preprocesser.py:** Loads the models and defines functions for summarization and grammar correction.

## License
This project is for educational purposes and uses models provided by Hugging Face under their respective licenses.

---
Enjoy your summarized, error-free text!


