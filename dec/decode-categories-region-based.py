#!/usr/bin/env python
# coding: utf-8

# In[28]:


import os
import pickle
from glob import glob

import pandas as pd
import numpy as np
import seaborn as sns
from matplotlib import pyplot as plt
from scipy.io import loadmat
from scipy.ndimage import gaussian_filter1d as smooth
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import StratifiedKFold

channels = pd.read_csv("/home/content/Desktop/cr/info/locations.txt", sep="\t", 
                       names=['no.', 'x', 'y', 'z', 'chName', 'reg'])
channels.to_pickle('/home/content/Desktop/cr/info/channels.pkl')


# In[29]:


# Select subject name
def print_prompt():
    os.system('cls')
    print("Select one of the subjects by entering the corresponding name")
    print("[0]: All of the Subjects")
    for iterator, name in enumerate(subjects):
        print(f"[{iterator + 1}]: {name.replace('-', ' ').title()}")

data_path = '/home/content/Desktop/cr/data'
subjects = []
for subject in glob(os.path.join(data_path, 'mat-*.mat')):
    name = '-'.join(os.path.basename(subject).split('.')[0].split('-')[1:3])
    subjects.append(name)
       
    
# Select region    

def print_region():
    print("Select one of the regions")
    print("[0]: All of the regions")
    for iterator, name in enumerate(regions):
        print(f"[{iterator + 1}]: {name}")
             


# In[31]:


channelsInfo = pd.read_pickle('/home/content/Desktop/cr/info/channels.pkl')

with open('/home/content/Desktop/cr/info/channels.pkl', 'rb') as fp:
    chInfo = pickle.load(fp)      
regions = np.unique(chInfo['reg'])


# In[34]:


index = -1
while (index < 0):
    print_prompt()
    index = input('Index: ')
    if index.isnumeric() and (int(index) in np.arange(0, len(subjects)+1)):
        index = int(index)
        break
    index = -1
    
regIDX = -1
while (regIDX < 0):
    print_region()
    regIDX = input('Index: ')
    if regIDX.isnumeric() & (int(regIDX) in np.arange(0, len(regions) + 1)):
        regIDX = int(regIDX)
        break

if index==0:
    acc, recall = [], []
    for subject_dir in glob('/home/content/Desktop/cr/data/*/'):
        if os.path.isfile(os.path.join(subject_dir, '__IGNORE_ME__')):
            continue
            
        cm = np.load(os.path.join(subject_dir, f'confusion-matrix-{region}.npy'))
        ac = np.diagonal(cm, axis1=2, axis2=3).sum(2) / cm.sum((2, 3)) * 100
        ac = smooth(ac, sigma=5)
        acc.append(ac.mean(0))
       
        rec = np.diagonal(cm, axis1=2, axis2=3) / cm.sum(3) * 100
        recall.append(rec.mean(0))

    acc, recall = np.array(acc), np.array(recall)

    d = loadmat(os.path.join('G:\Data\EEG', f'{subject}.mat'))
    time = d['time'].flatten()[np.arange(0, 750 - 50)] * 1000 + 25

    subject = '.'
else:
    if regIDX - 1 != -1:
        channels = chInfo[chInfo['reg']==regions[regIDX - 1]].index
        region = regions[regIDX - 1]
    else:
        channels = np.arange(len(channels['no.']))
        region = 'all-regions'
    subject = subjects[index - 1]

    # Load the data
    
    print(f'Loading data for subject : {subject}')
    d = loadmat(os.path.join('/home/content/Desktop/cr/data', f'mat-{subject}.mat'))
    print(f'Data loaded successfully')
    print(f'Loading stimulus info')
    with open('/home/content/Desktop/cr/info/info.pkl', 'rb') as fp:
        info = pickle.load(fp)
    print(f'Stimulus info loaded successfully')
    
    # Train classifiers
        
    categories = info.cat.to_numpy()[:155]
    y = categories[categories != 'none']
    X = d['X'][categories != 'none'][:, channels, :]
    kfold = StratifiedKFold(n_splits=7, shuffle=True, random_state=0)
    cm = []
    for train_index, test_index in kfold.split(X=y, y=y):
        X_train, X_test = X[train_index], X[test_index]
        y_train, y_test = y[train_index], y[test_index]
        
        rep = []
        
        for w0 in np.arange(0, X_train.shape[2] - 50):
            mdl = LinearDiscriminantAnalysis().fit(X_train[:,:,w0:w0+50].mean(2), y_train)
            rep.append(confusion_matrix(y_test, mdl.predict(X_test[:, :, w0:w0 + 50].mean(2)), labels=['face', 'body', 'artificial', 'natural']))
        cm.append(np.array(rep))
    cm = np.array(cm)
        
    # Save confusion matrix
    os.makedirs(os.path.join('/home/content/Desktop/cr/data', subject), exist_ok=True)
    np.save(os.path.join('/home/content/Desktop/cr/data', subject, f'confusion-matrix-{region}.npy'), cm)
    
    time = d['time'].flatten()[np.arange(0, X_train.shape[2] - 50)] * 1000 + 25
    acc = np.diagonal(cm, axis1=2, axis2=3).sum(2) / cm.sum((2, 3)) * 100
    acc = smooth(acc, sigma=5)
    recall = np.diagonal(cm, axis1=2, axis2=3) / cm.sum(3) * 100

            


# In[35]:


# Plot the LDA results
fig, axs = plt.subplots(1, 2, figsize=(14, 4), sharey=False)

axs[0].plot(time, acc.mean(0), lw=3)
axs[0].fill_between(time,
                 acc.mean(0) - acc.std(0),
                 acc.mean(0) + acc.std(0),
                 alpha=.1)

axs[0].set_title('Accuracy', fontsize=14)

for icat in np.arange(4):
    r = smooth(recall[:, :, icat], sigma=4, axis=-1)
    axs[1].plot(time, r.mean(0), lw=3)
    axs[1].fill_between(time,
                     r.mean(0) - r.std(0),
                     r.mean(0) + r.std(0),
                     alpha=.1)
axs[1].set_xlim(-50, 500)    
axs[1].legend(['Face', 'Body', 'Aartificial', 'Natural'], frameon=False)
axs[1].set_title('Recall', fontsize=14)

sns.despine()
for ax in axs:
    ax.tick_params(axis='both', which='major', labelsize=12)
    ax.axvline(0, c='gray', ls='--', label='_nolegend_')
    ax.axhline(25, c='gray', ls='--', label='_nolegend_')
    ax.axvline(170, c='gray', ls='--', label='_nolegend_')
    ax.set_xlim(-50, 500)
    # ax.set_ylim(0, 100)
fig.suptitle(f"LDA Performance on Subject: {subject.replace('-', ' ').title()} - {region.capitalize()}", fontsize=20)
fig.tight_layout()
plt.savefig(os.path.join('/home/content/Desktop/cr/data', subject, f'lda-{region}.jpg'), dpi=600)


# In[38]:


glob('/home/content/Desktop/cr/data/*/')
