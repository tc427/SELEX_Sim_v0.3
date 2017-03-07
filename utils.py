import time
import random
import linecache
import math
from math import factorial
from itertools import izip, imap
import operator
from collections import OrderedDict
from scipy import stats
import numpy as np




def seqNumberCounter(seqPool):
    totalSeqNum = int(0)
    uniqSeqNum = int(0)
    for seqIdx in seqPool:
        totalSeqNum += seqPool[seqIdx][0]
        uniqSeqNum += 1
    return int(totalSeqNum), int(uniqSeqNum)

# This computes the binomial coefficient (not used)
def binomCoeff(n, k):
    binom = factorial(n)/(factorial(k)*factorial(n-k))
    return binom

# This converts an array of probabilities into a
# discrete probability distribution
def convert_to_distribution(x, y, distName):
    xDist = stats.rv_discrete(name=distName, values=(x, y))
    return xDist

# Add method for computing the binomial coefficient

# Add method for computing the L1 norm 

# Add method to convert probability vectors to discrete distributions

def rvd(X, X_sum, distName):
    seqIdxs = np.zeros(X.shape[0])
    probs = np.zeros(X.shape[0])
    for i, seq in enumerate(X):
        seqIdxs[i] = i
        probs[i] = seq[1]/X_sum
    dist = stats.rv_discrete(name=distName, values=(seqIdxs, probs))
    return dist

