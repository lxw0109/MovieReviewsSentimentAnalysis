#!/usr/bin/env python3
# coding: utf-8
# File: preprocessing.py
# Author: lxw
# Date: 5/14/18 10:53 PM

import json
# import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
# import seaborn as sns
import time

from gensim.models import KeyedVectors
from gensim.models import word2vec
from keras.utils import np_utils
# from pyfasttext import FastText
from sklearn.model_selection import train_test_split


def fetch_data_df(train_path, test_path, sep="\t"):
    """
    :param train_path: path of train data.
    :param test_path:  path of test data.
    :param sep: 
    :return: return train_df and test_df **WITHOUT Normalization**.
    """
    train_df, test_df = None, None
    if train_path:
        train_df = pd.read_csv(train_path, sep=sep)  # (156060, 4)
    if test_path:
        test_df = pd.read_csv(test_path, sep=sep)  # (66292, 3)
    # print(train_df.describe())
    # print(test_df.describe())
    return train_df, test_df


def data_analysis(train_df, test_df):
    sns.set(style="white", context="notebook", palette="deep")

    Y_train = train_df["Sentiment"]
    X_train = train_df.drop(labels=["Sentiment"], axis=1)

    # free some space
    del train_df

    # 1. 查看样本数据分布情况(各个label数据是否均匀分布)
    sns.countplot(Y_train)
    plt.show()
    print(Y_train.value_counts())  # TODO: Is this an imbalanced dataset?
    """
    2    79582
    3    32927
    1    27273
    4     9206
    0     7072
    """

    # 2. Check for null and missing values
    # print(pd.DataFrame([1, 2, 3, np.nan, 1, 2, 3, -1, 3, 2, 1, 3, 2, np.nan, 3, 2, 1]).isnull().any())
    # print(pd.DataFrame([1, 2, 3, np.nan, 1, 2, 3, -1, 3, 2, 1, 3, 2, np.nan, 3, 2, 1]).isnull().any().describe())
    print(X_train.isnull().any().describe())  # no misssing values.
    print(test_df.isnull().any().describe())  # no misssing values.
    # fillna() if missing values occur.


def rm_stopwords(train_df, test_df):
    """
    分词 -> 去停用词
    生成文件"../data/output/train_wo_sw.csv"
    :param train_df: 
    :param test_df: 
    :return: 
    """
    # 1. load stopwords.
    stop_words_list = open("../data/input/snownlp_en_stopwords.txt").readlines()
    stop_words_set = set()
    for word in stop_words_list:
        word = word.strip()
        if word:
            stop_words_set.add(word)

    # 2. process train_df
    phrase_series = train_df["Phrase"]  # <Series>. shape: (156060,)
    sentiment_series = train_df["Sentiment"]  # <Series>. shape: (156060,)

    f = open("../data/output/train_wo_sw.csv", "wb")
    f.write("Phrase\tSentiment\n".encode("utf-8"))  # NOTE: 不能以逗号分割，因为数据中有逗号分割的词，例如数字中的分隔符
    for ind, phrase in enumerate(phrase_series):
        word_list = phrase.split()
        word_wo_sw = []
        for word in word_list:
            if word not in stop_words_set and word != "":
                word_wo_sw.append(word)
        # if word_wo_sw:  # 空的也得写入文件, 后面预测时也会出现空的情况, 所以这里需要在训练集中也出现
        f.write("{0}\t{1}\n".format(" ".join(word_wo_sw), sentiment_series.iloc[ind]).encode("utf-8"))
    f.close()

    # 3. process test_df
    phrase_series = test_df["Phrase"]  # <Series>. shape: (156060,)
    phrase_id_series = test_df["PhraseId"]  # <Series>. shape: (156060,)
    f = open("../data/output/test_wo_sw.csv", "wb")
    f.write("PhraseId\tPhrase\n".encode("utf-8"))
    for ind, phrase in enumerate(phrase_series):
        word_list = phrase.split()
        word_wo_sw = []
        for word in word_list:
            if word not in stop_words_set and word != "":
                word_wo_sw.append(word)
        # if word_wo_sw:  # 空的也得写入文件, 后面还是要进行预测的
        f.write("{0}\t{1}\n".format(phrase_id_series.iloc[ind], " ".join(word_wo_sw)).encode("utf-8"))
    f.close()


def data2vec(train_df, test_df):
    """
    word2vec(phrase2vec), 并将结果写入文件output/train_vector.csv, output/test_vector.csv
    :param train_df: 
    :param test_df: 
    :return: 
    """
    # 1. 加载模型
    start_time = time.time()
    model = KeyedVectors.load_word2vec_format("../data/input/models/GoogleNews-vectors-negative300.bin", binary=True)
    # model = FastText("/home/lxw/IT/program/github/NLP-Experiments/fastText/data/lxw_model_cbow.bin")  # OK
    # model = KeyedVectors.load_word2vec_format("/home/lxw/IT/program/github/NLP-Experiments/word2vec/data/"
    #                                           "corpus.model.bin", binary=True)
    end_time = time.time()
    print("Loading Model Time Cost: {}".format(end_time - start_time))
    model_word_set = set(model.index2word)
    vec_size = model.vector_size
    # model.index2entity == model.index2word: True
    # print(model.similarity("good", "bad"))  # 0.7190051208276236

    # 2. 生成Phrase vector
    # Reference: [在python中如何用word2vec来计算句子的相似度](https://vimsky.com/article/3677.html)
    senti_series = train_df["Sentiment"]  # <Series>. shape: (156060,)
    phrase_series = train_df["Phrase"]  # <Series>. shape: (156060,)
    f = open("../data/output/train_vector.csv", "wb")
    f.write("Phrase_vec\tSentiment\n".encode("utf-8"))  # NOTE: 不能以逗号分割，因为数据中有逗号分割的词，例如数字中的分隔符
    for ind, phrase in enumerate(phrase_series):
        phrase = str(phrase)
        phrase_vec = np.zeros((vec_size,), dtype="float32")
        word_count = 0
        word_list = phrase.split()
        for word in word_list:
            if word in model_word_set:
                word_count += 1
                phrase_vec = np.add(phrase_vec, model[word])
        if word_count > 0:
            phrase_vec = np.divide(phrase_vec, word_count)
        f.write("{0}\t{1}\n".format(json.dumps(phrase_vec.tolist()), senti_series.iloc[ind]).encode("utf-8"))
    f.close()

    phrase_id_series = test_df["PhraseId"]  # <Series>. shape: (156060,)
    phrase_series = test_df["Phrase"]  # <Series>. shape: (156060,)
    f = open("../data/output/test_vector.csv", "wb")
    f.write("PhraseId\tPhrase_vec\n".encode("utf-8"))  # NOTE: 不能以逗号分割，因为数据中有逗号分割的词，例如数字中的分隔符
    for ind, phrase in enumerate(phrase_series):
        phrase = str(phrase)
        phrase_vec = np.zeros((vec_size,), dtype="float32")
        word_count = 0
        word_list = phrase.split()
        for word in word_list:
            if word in model_word_set:
                word_count += 1
                phrase_vec = np.add(phrase_vec, model[word])
        if word_count > 0:
            phrase_vec = np.divide(phrase_vec, word_count)
        f.write("{0}\t{1}\n".format(phrase_id_series.iloc[ind], json.dumps(phrase_vec.tolist())).encode("utf-8"))
    f.close()


def data_preparation(train_df, test_df):
    y = train_df["Sentiment"]  # <Series>. shape: (156060,)
    y = np_utils.to_categorical(y)  # <ndarray of ndarray>. shape: (156060, 5)


if __name__ == "__main__":
    # train_df, test_df = fetch_data_df(train_path="../data/input/train.tsv",
    #                                   test_path="../data/input/test.tsv", sep="\t")
    # # data_analysis(train_df, test_df)
    # rm_stopwords(train_df, test_df)

    train_df, test_df = fetch_data_df(train_path="../data/output/train_wo_sw.csv",
                                      test_path="../data/output/test_wo_sw.csv", sep="\t")
    data2vec(train_df, test_df)
