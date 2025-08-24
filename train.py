import os
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

# Original Cache File
file_name = 'cache.csv'
base_dir = os.path.dirname(__file__)
file_path = os.path.join(base_dir, file_name)

# Final Cache File
f_name = 'encoded_cache.csv'
base_d = os.path.dirname(__file__)
f_path = os.path.join(base_dir, f_name)

def readCache(cache_file): 
    if os.path.exists(cache_file): 
        df = pd.read_csv(cache_file)
    return df

# One-Hot Encoding and Handles NaN Values
def encode(data): 
    df_encoded = pd.get_dummies(data, columns=['driver_id', 'constructor'], dtype=int)
    df_encoded = df_encoded.fillna(-1)
    return df_encoded
    
def writeToCache(cache_file, data):
    if os.path.exists(cache_file): 
        data.to_csv(cache_file, index=False)

#------------------------------------Commands----------------------------------------#
'''df = readCache(file_path)
encoded_df = encode(df)
writeToCache(f_path, encoded_df)'''

df = readCache(f_path)
# Training Set
X = df.drop('actual_result', axis=1)
# Testing Set
y = df['actual_result']

# Splitting Data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

#-----------------FROM-XGBOOST-DOCS-----------------------#
# create model instance
bst = XGBClassifier(n_estimators=2, max_depth=2, learning_rate=1, objective='binary:logistic')
# fit model
bst.fit(X_train, y_train)
# make predictions
preds = bst.predict(X_test)
print(preds)


