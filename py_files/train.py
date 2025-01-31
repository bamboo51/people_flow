import pandas as pd
import numpy as np
from utils import *
import argparse
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from joblib import dump
from model import create_model, train_model_ts

# argv
parser = argparse.ArgumentParser()
parser.add_argument('place', help='place for training')
parser.add_argument('window_size', help='window size')
args = parser.parse_args()

# read data
place = args.place
print(f'training at {place}')
path = f'../data/num_file/min_05/{place}.csv'
data = pd.read_csv(path)
print(f'read data...shape={data.shape}')

# make datetime as index
data['datetime'] = pd.to_datetime(data['date'])+pd.to_timedelta(data['hour'], unit='h')
data = data.drop(['date', 'hour'], axis=1)
data.set_index('datetime', inplace=True)
data.columns = ['amount']
data['amount'] = data['amount'].astype(float)

# generate missing index
full_index = pd.date_range(start=data.index.min(), end=data.index.max(), freq='h')
data = data.reindex(full_index)
data['amount'] = data['amount'].bfill()

# normalize data
index = data.index
scaler = StandardScaler()
scaler.fit(data)
dump(scaler, f'./param/scaler_{place}.joblib')
data = scaler.transform(data)
data = pd.DataFrame(data)
data.set_index(index, inplace=True)

# slice data to be window step
window_step = int(args.window_size)
data = one_step_forecast(data, window_step)

# split data
train, test = train_test_split(data, test_size=0.2, shuffle=False)
train, val = train_test_split(train, test_size=0.05, shuffle=False)
x = [f'x_{i}' for i in range(1, window_step+1)]
y = ['y']
x_train, y_train = np.expand_dims(train[x], axis=-1), np.expand_dims(train[y], axis=-1)
x_test, y_test = np.expand_dims(test[x], axis=-1), np.expand_dims(test[y], axis=-1)
x_val, y_val = np.expand_dims(val[x], axis=-1), np.expand_dims(val[y], axis=-1)

# training model
model = create_model(train=x_train, units=32)
print(model.summary())
history = train_model_ts(model, x_train, y_train, x_val, y_val)
predict = model.predict(x_test)
print('======evaluate=======')
eval_hist = model.evaluate(x_test, y_test)
eval_hist = scaler.inverse_transform(np.array(eval_hist).reshape(-1, 1))
print(eval_hist)

# inverse value
y_test = scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()
predict = scaler.inverse_transform(predict.reshape(-1, 1)).flatten()
file_name = f'{place}_{window_step}'
plot_forecast(y_test, predict, test.index, history, eval_hist, file_name, window_step)
plot_error(y_test, predict, test.index, file_name, window_step)

# saving model
path = f'./param/lstm_w{window_step}.keras'
print(f"save model as {path}")
model.save(path)