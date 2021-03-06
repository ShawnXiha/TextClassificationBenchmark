# -*- coding: utf-8 -*-
import torch
import torch.nn.functional as F
from torchtext import data
from torchtext import datasets
from torchtext.vocab import Vectors, GloVe, CharNGram, FastText
import numpy as np
from functools import wraps
import time

def log_time_delta(func):
    @wraps(func)
    def _deco(*args, **kwargs):
        start = time.time()
        ret = func(*args, **kwargs)
        end = time.time()
        delta = end - start
        print( "%s runed %.2f seconds"% (func.__name__,delta))
        return ret
    return _deco  

def clip_gradient(optimizer, grad_clip):
    for group in optimizer.param_groups:
        for param in group['params']:       
            if param.grad is not None and param.requires_grad:
                param.grad.data.clamp_(-grad_clip, grad_clip)


def loadData(opt):

    device = 0 if  torch.cuda.is_available()  else -1

    TEXT = data.Field(lower=True, include_lengths=True, batch_first=True,fix_length=opt.max_seq_len)
    LABEL = data.Field(sequential=False)
    if opt.dataset=="imdb":
        train, test = datasets.IMDB.splits(TEXT, LABEL)
    elif opt.dataset=="sst":
        train, val, test = datasets.SST.splits( TEXT, LABEL, fine_grained=True, train_subtrees=True,
                                               filter_pred=lambda ex: ex.label != 'neutral')
    elif opt.dataset=="trec":
        train, test = datasets.TREC.splits(TEXT, LABEL, fine_grained=True)
    else:
        print("does not support this datset")
        
    TEXT.build_vocab(train, vectors=GloVe(name='6B', dim=300))
    LABEL.build_vocab(train)    
    # print vocab information
    print('len(TEXT.vocab)', len(TEXT.vocab))
    print('TEXT.vocab.vectors.size()', TEXT.vocab.vectors.size())

    train_iter, test_iter = data.BucketIterator.splits((train, test), batch_size=opt.batch_size,device=device,repeat=False,shuffle=True)

    opt.label_size= len(LABEL.vocab)    
    opt.vocab_size = len(TEXT.vocab)
    opt.embedding_dim= TEXT.vocab.vectors.size()[1]
    opt.embeddings = TEXT.vocab.vectors
    
    return train_iter, test_iter


def evaluation(model,test_iter,from_torchtext=True):
    model.eval()
    accuracy=[]
#    batch= next(iter(test_iter))
    for index,batch in enumerate( test_iter):
        text = batch.text[0] if from_torchtext else batch.text
        predicted = model(text)
        prob, idx = torch.max(predicted, 1) 
        percision=(idx== batch.label).float().mean()
        
        if torch.cuda.is_available():
            accuracy.append(percision.data.cpu().numpy()[0] )
        else:
            accuracy.append(percision.data.numpy()[0] )
    model.train()
    return np.mean(accuracy)

def getLogger():
    import sys
    import logging
    import os
    import time
    now = int(time.time()) 
    timeArray = time.localtime(now)
    timeStamp = time.strftime("%Y%m%d%H%M%S", timeArray)
    log_filename = "log/" +time.strftime("%Y%m%d", timeArray)
    
    program = os.path.basename(sys.argv[0])
    logger = logging.getLogger(program) 
    if not os.path.exists(log_filename):
        os.mkdir(log_filename)
    logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',datefmt='%a, %d %b %Y %H:%M:%S',filename=log_filename+'/qa'+timeStamp+'.log',filemode='w')
    logging.root.setLevel(level=logging.INFO)
    logger.info("running %s" % ' '.join(sys.argv))
    
    return logger

