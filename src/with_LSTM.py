#!/usr/bin/env python3
# coding: utf-8
# File: with_LSTM.py
# Author: lxw
# Date: 6/6/18 5:26 PM

import json
import numpy as np
import pandas as pd
import pickle
import tensorflow as tf
import time

from keras import Sequential
from keras.callbacks import EarlyStopping
from keras.callbacks import ModelCheckpoint
from keras.callbacks import ReduceLROnPlateau
from keras.layers import Dense
from keras.layers import Dropout
from keras.layers import Embedding
from keras.layers import LSTM
from keras.layers import Masking
from keras.models import load_model
# from keras.optimizers import Adam
from keras.utils import np_utils

from preprocessing import data2vec_bow
from preprocessing import gen_train_val_test_data
from preprocessing import gen_train_val_test_matrix


def model_build(input_shape, num_classes=5):
    """
    :param input_shape: 
    :return: 
    """
    model = Sequential()

    model.add(Masking(mask_value=-1, input_shape=input_shape, name="masking_layer"))
    # The way Keras LSTM layers work is by taking in a numpy array of 3 dimensions (N, W, F) where N is the
    # number of training sequences, W is the sequence length and F is the number of features of each sequence.
    # model.add(LSTM(units=64, input_shape=input_shape, return_sequences=True, name="lstm1"))
    model.add(LSTM(units=64, return_sequences=True, name="lstm1"))
    # model.add(GRU(units=64, input_shape=input_shape, return_sequences=True, name="gru1"))
    model.add(Dropout(0.25, name="dropout2"))

    model.add(LSTM(units=128, return_sequences=False, name="lstm3"))
    # model.add(GRU(units=128, return_sequences=False, name="gru3"))
    model.add(Dropout(0.25, name="dropout4"))

    """
    model.add(LSTM(units=128, return_sequences=True, name="lstm7"))
    # model.add(GRU(units=layers[2], return_sequences=False, name="gru7"))
    model.add(Dropout(0.25, name="dropout8"))

    model.add(LSTM(units=128, return_sequences=True, name="lstm9"))
    model.add(Dropout(0.25, name="dropout10"))

    model.add(LSTM(units=128, return_sequences=False, name="lstm11"))
    model.add(Dropout(0.25, name="dropout12"))

    model.add(LSTM(units=layers[5], return_sequences=False, name="lstm13"))
    model.add(Dropout(0.25, name="dropout14"))
    """

    model.add(Dense(units=num_classes, activation="softmax", name="dense5"))

    start = time.time()

    # model.load_weights("../data/output/models/best_model_08_0.92.hdf5")  # OK: 加载模型权重  # DEBUG

    # optimizer="rmsprop". This optimizer is usually a good choice for Recurrent Neural Networks.
    # model.compile(loss="categorical_crossentropy", optimizer="rmsprop", metrics=["accuracy"])
    model.compile(loss="categorical_crossentropy", optimizer="adam", metrics=["accuracy"])
    """
    adam_opt = Adam(lr=1e-4)
    model.compile(loss="categorical_crossentropy", optimizer=adam_opt, metrics=["accuracy"])    # 默认lr为1e-3,调整为1e-4
    """
    print("> Compilation Time: ", time.time() - start)

    return model


def model_train_val(X_train, X_val, y_train, y_val):
    print(len(X_train.shape))
    if len(X_train.shape) == 2:  # 2: vector.  3: matrix.
        X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))
        X_val = np.reshape(X_val, (X_val.shape[0], X_val.shape[1], 1))
    print("X_train.shape:{0}\nX_val.shape:{1}\n".format(X_train.shape, X_val.shape))

    BATCH_SIZE = 512
    EPOCHS = 300
    model = model_build(input_shape=(X_train.shape[1], X_train.shape[2]))

    early_stopping = EarlyStopping(monitor="val_loss", patience=10)
    # NOTE: It's said and I do think monitor="val_loss" is better than "val_acc".
    # Reference: [Should we watch val_loss or val_acc in callbacks?](https://github.com/raghakot/keras-resnet/issues/41)
    # lr_reduction = ReduceLROnPlateau(monitor="val_loss", patience=5, verbose=1, factor=0.2, min_lr=1e-6)  # DEBUG
    lr_reduction = ReduceLROnPlateau(monitor="val_loss", patience=5, verbose=1, factor=0.2, min_lr=1e-5)
    # 检查最好模型: 只要有提升, 就保存一次
    model_path = "../data/output/models/best_model_{epoch:02d}_{val_loss:.2f}.hdf5"  # 保存到多个模型文件
    # model_path = "../data/output/models/best_model.hdf5"  # 保存到1个模型文件(因为文件名相同)
    checkpoint = ModelCheckpoint(filepath=model_path, monitor="val_loss", verbose=1, save_best_only=True, mode="min")

    # hist_obj = model.fit(X_train, y_train, batch_size=BATCH_SIZE, epochs=EPOCHS, validation_split=0.1)
    hist_obj = model.fit(X_train, y_train, batch_size=BATCH_SIZE, epochs=EPOCHS, verbose=1,
                         validation_data=(X_val, y_val), callbacks=[early_stopping, lr_reduction, checkpoint])
    with open(f"../data/output/history_{BATCH_SIZE}.pkl", "wb") as f:
        pickle.dump(hist_obj.history, f)

    # model.save(f"../data/output/models/lstm_{BATCH_SIZE}.model")


def model_predict(model, X_test, X_test_id, X_val, y_val):
    # Generate predicted result.
    print(len(X_test.shape))
    if len(X_test.shape) == 2:  # 2: vector.  3: matrix.
        X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
        X_val = np.reshape(X_val, (X_val.shape[0], X_val.shape[1], 1))
    print("X_test.shape:{0}\nX_val.shape:{1}\n".format(X_test.shape, X_val.shape))
    predicted = model.predict(X_test)  # predicted.shape: (, )
    print(f"predicted.shape: {predicted.shape}")
    """
    # print(predicted[:10])  # OK
    [[ 0.17622797  0.17507555  0.27694944  0.19135155  0.18039554]
     ...
     [ 0.17644432  0.17531542  0.27615064  0.19144376  0.18064587]
     [ 0.17644432  0.17531542  0.27615064  0.19144376  0.18064587]
     [ 0.17644432  0.17531544  0.27615064  0.19144376  0.18064587]]
    """
    # 把categorical数据转为numeric值，得到分类结果
    predicted = np.argmax(predicted, axis=1)
    """
    np.savetxt("../data/output/lstm_submission.csv", np.c_[range(1, len(X_test) + 1), predicted], delimiter=",",
               header="PhraseId,Sentiment", comments="", fmt="%d")
    """
    predicted = pd.Series(predicted, name="Sentiment")
    submission = pd.concat([X_test_id, predicted], axis=1)
    submission.to_csv("../data/output/submissions/lstm_submission_matrix.csv", index=False)

    # Model Evaluation
    print("model.metrics:{0}, model.metrics_names:{1}".format(model.metrics, model.metrics_names))
    scores = model.evaluate(X_val, y_val)
    loss, accuracy = scores[0], scores[1] * 100
    print("Loss: {0:.2f}, Model Accuracy: {1:.2f}%".format(loss, accuracy))


def gen_submission():
    submission_df = pd.read_csv("../data/output/submissions/lstm_submission_matrix.csv", index_col=0)
    # submission_df = pd.read_csv("../data/output/submissions/sk_rf_submission_matrix.csv", index_col=0)
    with open("../data/output/submissions/empty_matrix_list_test.txt") as f:
        most_senti = f.readline().strip()
        phrase_id_list = json.loads(f.readline().strip())  # <list of int>. length: 2338
    empty_ids_df = pd.DataFrame(most_senti, index=phrase_id_list, columns=["Sentiment"])
    submission_df = submission_df.append(empty_ids_df)
    submission_df.index.name = "PhraseId"
    submission_df.sort_index(inplace=True)
    submission_df.to_csv("../data/output/submissions/lstm_submission_matrix_fill.csv")
    # submission_df.to_csv("../data/output/submissions/sk_rf_submission_matrix_fill.csv")


def model_train_val_bow(X_train, X_val, y_train, y_val, vocab_size, max_sent_len):
    BATCH_SIZE = 512
    EPOCHS = 300

    model = Sequential()

    # TODO: 128, 64, 64 or 32, 网络结构的调整
    model.add(Embedding(input_dim=vocab_size+1, output_dim=64, input_length=max_sent_len,
                        mask_zero=False, name="embedding"))  # TODO: mask_zero=True
    model.add(LSTM(units=64, return_sequences=True, dropout=0.25, name="lstm1"))

    model.add(LSTM(units=128, return_sequences=False, dropout=0.25, name="lstm2"))

    model.add(Dense(units=5, activation="softmax", name="dense3"))
    model.compile(loss="categorical_crossentropy", optimizer="adam", metrics=["accuracy"])

    early_stopping = EarlyStopping(monitor="val_loss", patience=10)
    lr_reduction = ReduceLROnPlateau(monitor="val_loss", patience=5, verbose=1, factor=0.2, min_lr=1e-5)
    # 检查最好模型: 只要有提升, 就保存一次
    model_path = "../data/output/models/best_model_{epoch:02d}_{val_loss:.2f}.hdf5"  # 保存到多个模型文件
    # model_path = "../data/output/models/best_model.hdf5"  # 保存到1个模型文件(因为文件名相同)
    checkpoint = ModelCheckpoint(filepath=model_path, monitor="val_loss", verbose=1, save_best_only=True, mode="min")

    # hist_obj = model.fit(X_train, y_train, batch_size=BATCH_SIZE, epochs=EPOCHS, validation_split=0.1)
    hist_obj = model.fit(X_train, y_train, batch_size=BATCH_SIZE, epochs=EPOCHS, verbose=1, 
                         validation_data=(X_val, y_val), callbacks=[early_stopping, lr_reduction, checkpoint])  # shuffle默认值是True
    """
    # NOTE: 上一行中validation_data改成validation_split=0.3后准确率下降了5~6个百分点:
    当使用validation_split时"The validation data is selected from the last samples in the x and y data provided, before shuffling."
    准确率下降可能和shuffle是有关的, 因为是在shuffle之前进行的切割，可能训练集、验证集的数据均衡性分布有问题，导致训练效果变差
    "shuffle: whether to shuffle the training data before each epoch"

    此外, 本来使用validation_split是想使用交叉验证的，但似乎并不会起到交叉验证的作用(不一定，需要进一步确认)，
    只是把这些数据剔除出来不进行训练, 和sklearn的train_test_split是一样的，但train_test_split提供了shuffle，
    所以还是train_test_split好些
    """

    with open(f"../data/output/history_{BATCH_SIZE}.pkl", "wb") as f:
        pickle.dump(hist_obj.history, f)


def model_predict_bow(model, X_test, X_test_id, X_val, y_val):
    # Generate predicted result.
    print("X_test.shape:{0}\nX_val.shape:{1}\n".format(X_test.shape, X_val.shape))
    predicted = model.predict(X_test)  # predicted.shape: (, )
    print(f"predicted.shape: {predicted.shape}")
    """
    # print(predicted[:10])  # OK
    [[ 0.17622797  0.17507555  0.27694944  0.19135155  0.18039554]
     ...
     [ 0.17644432  0.17531542  0.27615064  0.19144376  0.18064587]
     [ 0.17644432  0.17531542  0.27615064  0.19144376  0.18064587]
     [ 0.17644432  0.17531544  0.27615064  0.19144376  0.18064587]]
    """
    # 把categorical数据转为numeric值，得到分类结果
    predicted = np.argmax(predicted, axis=1)
    """
    np.savetxt("../data/output/lstm_submission.csv", np.c_[range(1, len(X_test) + 1), predicted], delimiter=",",
               header="PhraseId,Sentiment", comments="", fmt="%d")
    """
    predicted = pd.Series(predicted, name="Sentiment")
    submission = pd.concat([X_test_id, predicted], axis=1)
    submission.to_csv("../data/output/submissions/lstm_submission_bow.csv", index=False)

    # Model Evaluation
    print("model.metrics:{0}, model.metrics_names:{1}".format(model.metrics, model.metrics_names))
    scores = model.evaluate(X_val, y_val)
    loss, accuracy = scores[0], scores[1] * 100
    print("Loss: {0:.2f}, Model Accuracy: {1:.2f}%".format(loss, accuracy))


def plot_hist():
    import matplotlib.pyplot as plt

    history = None
    with open("../data/output/history/history_1024.pkl", "rb") as f:  # DEBUG
        history = pickle.load(f)
    if not history:
        return
    # 绘制训练集和验证集的曲线
    plt.plot(history["acc"], label="Training Accuracy", color="green", linewidth=2)
    plt.plot(history["loss"], label="Training Loss", color="red", linewidth=1)
    plt.plot(history["val_acc"], label="Validation Accuracy", color="purple", linewidth=2)
    plt.plot(history["val_loss"], label="Validation Loss", color="blue", linewidth=1)
    plt.grid(True)  # 设置网格形式
    plt.xlabel("epoch")
    plt.ylabel("acc-loss")  # 给x, y轴加注释
    plt.legend(loc="upper right")  # 设置图例显示位置
    plt.show()


if __name__ == "__main__":
    # For reproducibility
    np.random.seed(2)
    tf.set_random_seed(2)

    # X_train, X_val, X_test, X_test_id, y_train, y_val = gen_train_val_test_data()  # vector
    # X_train, X_val, X_test, X_test_id, y_train, y_val = gen_train_val_test_matrix()  # matrix
    X_train, X_val, X_test, X_test_id, y_train, y_val, vocab_size, max_sent_len = data2vec_bow()  # "BOW" vector
    # X_train, y_train, X_test, X_test_id, vocab_size, max_sent_len = data2vec_bow()  # "BOW" vector

    print(f"X_train.shape:{X_train.shape}\ny_train.shape:{y_train.shape}\n"
          f"X_test.shape:{X_test.shape}\nX_test_id.shape:{X_test_id.shape}\n")

    """
    print("X_train.shape:{0}\nX_val.shape:{1}\nX_test.shape:{2}\nX_test_id.shape:{3}\n"
          "y_train.shape:{4}\ny_val.shape:{5}\n".format(X_train.shape, X_val.shape, X_test.shape,
                                                         X_test_id.shape, y_train.shape, y_val.shape))
    """

    # model_train_val(X_train, X_val, y_train, y_val)
    # model_train_val_bow(X_train, X_val, y_train, y_val, vocab_size, max_sent_len)

    # plot_hist()

    """
    model = load_model("../data/output/models/matrix_v6.0_best_model_20_0.81.hdf5")
    model_predict(model, X_test, X_test_id, X_val, y_val)

    gen_submission()
    """

    model = load_model("../data/output/models/best_model_04_0.85.hdf5")
    model_predict_bow(model, X_test, X_test_id, X_val, y_val)
