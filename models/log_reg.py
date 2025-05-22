import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support, accuracy_score
import pickle 
from pathlib import Path
from data.data import getData

def train_lg():
    
    file_path = f"{Path(__file__).parent.parent}"

    X_train, y_train, X_test, y_test = getData()

    print(y_train)
    log_reg = LogisticRegression(solver='lbfgs', multi_class='multinomial', max_iter=1000)
    log_reg.fit(X_train, y_train)

    test_lg(log_reg, X_test, y_test)
    
    with open(f"{file_path}/weights/lg.pkl", 'wb') as f:
        pickle.dump(log_reg, f)
        
    return log_reg

def test_lg(model: LogisticRegression, xtest, ytest):
    pred = model.predict(xtest)
    accuracy = accuracy_score(ytest, pred)
    precision, recall, f1, support = precision_recall_fscore_support(
        ytest, 
        pred, 
        average='weighted'
    )
    
    print(f"\nModel: LogisticRegression")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1 Score: {f1:.4f}")
    
    