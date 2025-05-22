import streamlit as st
import pickle
from pathlib import Path
from PIL import Image, ImageOps
import numpy as np
# Load the model
file_path = Path(__file__).parent
with open(f"{file_path}/weights/lg.pkl", 'rb') as f:
    log_reg_model = pickle.load(f) 

st.title("MNIST Digit Classifier")

# Model selection (you can add more models later)
model_choice = st.selectbox("Select a model:", ["Logistic Regression"])

# Image uploader
uploaded_file = st.file_uploader("Upload a digit image (handwritten, ideally on black background)", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Display original image
    st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)

    # Open and process the image
    img = Image.open(uploaded_file).convert("L")  # Convert to grayscale
    img_resized = img.resize((28, 28))  # Resize to 28x28

    # Optional: Invert if background is dark
    # img_resized = ImageOps.invert(img_resized)


    # Convert to numpy and normalize
    img_array = np.array(img_resized).reshape(1, 28*28) / 255.0

    # Predict
    prediction = log_reg_model.predict(img_array)[0]
    st.success(f"Predicted Digit: **{prediction}**")
