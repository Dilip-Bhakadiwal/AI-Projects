from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import os

# Local paths to your models
model_path_summarizer = "C:/Users/9828d/Desktop/project/model_2"
model_path_grammar = "C:/Users/9828d/Desktop/project/model_1"

# Check if the model directories exist
if not os.path.exists(model_path_summarizer) or not os.path.exists(model_path_grammar):
    raise FileNotFoundError("Model paths are incorrect or models are missing in the directories.")
else:
    print("Model paths verified.")

# Load Pretrained Models from local path
tokenizer_summarizer = AutoTokenizer.from_pretrained(model_path_summarizer)
model_summarizer = AutoModelForSeq2SeqLM.from_pretrained(model_path_summarizer)

tokenizer_grammar = AutoTokenizer.from_pretrained(model_path_grammar)
model_grammar = AutoModelForSeq2SeqLM.from_pretrained(model_path_grammar)

# Test model loading
print("Models and tokenizers loaded successfully.")

def correct_grammar(text):
    inputs = tokenizer_grammar.encode("gec: " + text, return_tensors="pt", max_length=512, truncation=True)
    outputs = model_grammar.generate(inputs, max_length=512, num_beams=4, early_stopping=True)
    corrected_text = tokenizer_grammar.decode(outputs[0], skip_special_tokens=True)
    return corrected_text

def clean_text(text):
    return correct_grammar(text)

def summarize_text(text):
    inputs = tokenizer_summarizer.encode(text, return_tensors="pt", max_length=512, truncation=True)
    outputs = model_summarizer.generate(inputs, max_length=150, num_beams=4, early_stopping=True)
    summarized_text = tokenizer_summarizer.decode(outputs[0], skip_special_tokens=True)
    return summarized_text
