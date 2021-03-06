import functools

from scipy import stats
import numpy as np
from numpy import random
from numpy.random import binomial as binom, poisson
from math import factorial as fact
from sklearn.preprocessing import normalize
import utils

# append ViennaRNA package to python path
import RNA


class Mutation(object):
    # constructor
    def __init__(self,
                 dist,
                 seqLength=0,
                 mutatedPool=None,
                 aptamerSeqs=None,
                 errorRate=0,
                 pcrCycleNum=0, pcrYld=0,
                 seqPop=None):
        # initialize parameters
        self.dist = dist
        self.seqLength = seqLength
        self.mutatedPool = mutatedPool
        self.aptamerSeqs = aptamerSeqs
        self.errorRate = errorRate
        self.pcrCycleNum = pcrCycleNum
        self.pcrYld = pcrYld
        self.seqPop = seqPop
        # add error handling for invalid param values

    # This method computes the probability of drawing a seq after each pcr cycle
    def get_cycleNumber_probabilities(self, seqPop):
        # normalize each element so that they all sum to one (i.e. probability measures)
        cycleNumProbs = normalize(seqPop.reshape(1, -1), norm='l1')[0]
        return cycleNumProbs

    # This method computes the distribution of drawing seqs after the different pcr cycles
    def get_cycleNumber_distribution(self, seqPop):
        N = self.pcrCycleNum
        cycleNumProbs = normalize(seqPop.reshape(1, -1), norm='l1')[0]
        cycleVec = np.arange(N)
        # compute discrete distribution
        cycleNumDist = stats.discrete.rv_discrete(name='cycleNumDist',
                                                  values=(cycleVec, cycleNumProbs))
        return cycleNumDist
# TEST AREA
# mut = Mutation()
# mutDist = mut.get_distribution(20, 0.000006, 0.85, 15)

    # This method computes the probabilities of each possible number of mutations (1-seqLength)
    # These probabilities can used to approximated the fraction of sequences that will undergo
    # certain numbers of mutation, assuming sequence count is sufficiently large
    def get_mutation_probabilities(self):
        L = self.seqLength
        N = self.pcrCycleNum
        e = self.errorRate
        y = self.pcrYld
        mutNumProbs = np.zeros(L+1)
        for m in range(L):
            for n in range(1, N+1, 1):
                mutNumProbs[m+1] += np.exp(-n*e*L) * \
                                    (n*e*L)**(m+1) * \
                                    fact(N)*y**(n) / \
                                    (fact(m+1)*fact(n)*fact(N-n)*(1+y)**(n))
            mutNumProbs[0] += mutNumProbs[m+1]
        mutNumProbs[0] = 1 - mutNumProbs[0]
        return mutNumProbs

    # This method computes the probabilities of each possible number of mutations (1-seqLength)
    # These probabilities can used to approximated the fraction of sequences that will undergo
    # certain numbers of mutation, assuming sequence count is sufficiently large
    def get_mutation_probabilities_original(self):
        L = self.seqLength
        e = self.errorRate
        mutNumProbs = np.zeros(L+1)
        lamb = L*e
        for m in range(L+1):
            mutNumProbs[m] = lamb**(m)*np.exp(-lamb)/(fact(m))
        return mutNumProbs

    # This method computes the discrete distribution of number of mutations (1-seqLength)
    # This distribution can be used to draw random numbers of mutations
    # The method is relatively slow but can be used when sequence count is small
    def get_mutation_distribution(self):
        L = self.seqLength
        N = self.pcrCycleNum
        e = self.errorRate
        y = self.pcrYld
        prob_m = np.zeros(L+1)
        # for each mutation number
        for m in range(L):
            # compute the probability for it to occur
            for n in range(1, N+1, 1):
                prob_m[m+1] += np.exp(-n*e*L) * \
                               (n*e*L)**(m+1) * \
                               fact(N)*y**(n) / \
                               (fact(m+1)*fact(n)*fact(N-n)*(1+y)**(n))
            prob_m[0] += prob_m[m+1]
        prob_m[0] = 1 - prob_m[0]
        # initialize vector containing each possible number of mutations (1-seqLength)
        mut_m = np.arange(L+1)
        # compute mutation number distribution
        mutDist = stats.rv_discrete(name='mutDist', values=(mut_m, prob_m))
        return mutDist

    # This method computes the probabilities of each possible number of mutations (1-seqLength)
    # These probabilities can used to approximated the fraction of sequences that will undergo
    # certain numbers of mutation, assuming sequence count is sufficiently large
    def get_mutation_distribution_original(self):
        L = self.seqLength
        e = self.errorRate
        mutNumProbs = np.zeros(L+1)
        lamb = L*e
        for m in range(L+1):
            mutNumProbs[m] = lamb**(m)*np.exp(-lamb)/(fact(m))
        mut_m = np.arange(L+1)
        mutDist = stats.rv_discrete(name='Poisson-based mutation distribution',
                                    values=(mut_m, mutNumProbs))
        return mutDist

    def choose_dist(self, distname, distance, aptamerSeqs):
        # compute 2D structure of aptamer(s)
        # find loop in 2D structure
        if distname == "hamming":
            return functools.partial(self.dist.hamming_func, aptamerSeqs)
        if distname == "random":
            return functools.partial(self.dist.nodist_func, aptamerSeqs)
        aptamerSeqsStruct = RNA.fold(str(aptamerSeqs))[0]
        if distname == "basepair":
            return functools.partial(self.dist.bp_func, aptamerSeqsStruct)
        aptamerLoop = utils.apt_loopFinder(aptamerSeqs, aptamerSeqsStruct, self.seqLength)
        if distname == "loop":
            return functools.partial(self.dist.loop_func, aptamerSeqs, aptamerSeqsStruct, aptamerLoop, self.seqLength)

    # This method aims to carry out the mutations on the pool of sequences that are in
    # the given mutated pool. It also updates the counts of the wild-type sequence and their
    # mutated variants to take into account pcr amplification during the process
    def generate_mutants(self,
                         mutatedPool, amplfdSeqs,
                         aptamerSeqs, apt, distname):
        pcrCycleNum = self.pcrCycleNum
        pcrYld = self.pcrYld
        seqLength = self.seqLength
        # initialize distance class
        d = self.dist
        md = self.choose_dist(distname, d, aptamerSeqs)
        # for each seq in the mutation pool
        for si, seqIdx in enumerate(mutatedPool):
            # grab probabilities to draw it after each pcr cycle
            cycleNumProbs = amplfdSeqs[seqIdx][3:]
            # print cycleNumProbs
            # compute a discrete distribution from probabilities
            cycleNumDist = stats.rv_discrete(name='cycleNumDist',
                                             values=(np.arange(pcrCycleNum), cycleNumProbs))
            # print cycleNumDist.rvs(size=10)
            # for each mutation instance for the seq
            for mutNum, mutFreq in enumerate(mutatedPool[seqIdx]):
                mutFreq = int(mutatedPool[seqIdx][mutNum])
                # if the mutation is carried out on less than 10,000 copies, draw random numbers...:(
                if mutFreq == 0:
                    continue
                elif mutFreq < 10000:
                    # draw random cycle numbers after which the sequences were drawn for mutation
                    cycleNums = cycleNumDist.rvs(size=mutFreq)
                    # generate the wild-type sequence string
                    wildTypeSeq = apt.pseudoAptamerGenerator(seqIdx)
                    # for each copy to be mutated
                    for mut in range(mutFreq):
                        wildTypeCount = 1
                        mutantCount = 1
                        # draw random positions on the seq to mutate
                        randPos = random.randint(1, seqLength+1, size=mutNum+1)
                        # draw a random nucleotide for each position
                        randNucs = random.randint(apt.La, size=mutNum+1)
                        mutatedSeq = wildTypeSeq
                        # for each position in seq, replace with random nucleotide
                        for posNum, pos in enumerate(randPos):
                            mutatedSeq = mutatedSeq[:(pos-1)] + apt.alphabetSet[randNucs[posNum]] + \
                                         mutatedSeq[pos:]
                        # generate index of mutant based on string
                        mutatedSeqIdx = apt.pseudoAptamerIndexGenerator(mutatedSeq)
                        # if mutant not found in amplified pool
                        if mutatedSeqIdx not in amplfdSeqs:
                            # add seq and its info to the amplified pool
                            mutDist = md(mutatedSeq)
                            mutBias = d.bias_func(mutatedSeq, seqLength)
                            amplfdSeqs[mutatedSeqIdx] = np.array([mutantCount,
                                                                  mutDist, mutBias])
                        # mutantNum = (1+pcrYld)**(pcrCycleNum - cycleNums[mut])
                        # for each pcr cycle after mutation has occured
                        for n in range(pcrCycleNum-cycleNums[mut]):
                            # compute amplified mutant count
                            mutantCount += int(binom(mutantCount,
                                               pcrYld+amplfdSeqs[mutatedSeqIdx][2]))
                            # compute loss of count from wild-type
                            wildTypeCount += int(binom(wildTypeCount,
                                                 pcrYld+amplfdSeqs[seqIdx][2]))
                        # increment mutant seq count in amplified pool
                        amplfdSeqs[mutatedSeqIdx][0] += mutantCount
                        # decrement wild-type seq count in amplfied pool
                        amplfdSeqs[seqIdx][0] -= wildTypeCount
                # if mutation carried out on more than 10,000 copies, avoid drawing random nums
                elif mutFreq > 10000:
                    # calculate fraction of mutants for each possible mutation
                    initialMutCount = int(0.333*mutFreq/seqLength)
                    # for each possible position that mutation can occur
                    for seqPos in range(seqLength):
                        # grab the sequence encoding array
                        seqArray = apt.get_seqArray(seqIdx)
                        # original nucleotide index
                        oni = seqArray[seqPos]
                        # mutated nucleotide index
                        for mni in range(4):
                            # skip if same residue
                            if mni == oni:
                                continue
                            mnd = mni-oni
                            mutatedSeqIdx = seqIdx+(4**(seqLength-seqPos-1)*mnd)
                            # if the mutated seq is not found in amplified pool
                            if mutatedSeqIdx not in amplfdSeqs:
                                # generate seq string using its index
                                mutatedSeq = apt.pseudoAptamerGenerator(mutatedSeqIdx)
                                mutDist = md(mutatedSeq)
                                # compute bias score of seq
                                mutBias = d.bias_func(mutatedSeq, seqLength)
                                # add to amplified pool
                                amplfdSeqs[mutatedSeqIdx] = np.array([0, mutDist, mutBias])
                            for cycleNum, cycleNumProb in enumerate(cycleNumProbs):
                                # compute expected number of mutant copies after amplification
                                amplfdSeqs[mutatedSeqIdx][0] += int(cycleNumProb *
                                                                    initialMutCount *
                                                                    (1+pcrYld)**(pcrCycleNum-cycleNum))
                                # compute expected decrease in no. of wild type seq
                                amplfdSeqs[seqIdx][0] -= int(cycleNumProb*initialMutCount *
                                                             (1+pcrYld)**(pcrCycleNum-cycleNum))
            if si % 1000 == 0:
                print("Mutated {:6.2f}%".format(100.0*si/len(mutatedPool)))
        print("Mutation has been carried out")
        return amplfdSeqs

    # This method aims to carry out the mutations on the pool of sequences that are in
    # the given mutated pool. It also updates the counts of the wild-type sequence and their
    # mutated variants to take into account pcr amplification during the process
    def generate_mutants_new(self, amplfdSeqs, aptamerSeqs, apt, distname):
        pcrCycleNum = self.pcrCycleNum
        pcrYld = self.pcrYld
        # calculate probabilities of different possible mutation numbers
        mutNumProbs = self.get_mutation_probabilities_original()
        # initialize distance class
        d = self.dist
        md = self.choose_dist(distname, d, aptamerSeqs)
        # save copy number
        prevSeqs = [k for k in amplfdSeqs.keys()]
        prevCopies = [v[0] for v in amplfdSeqs.values()]
        Lc = len(prevCopies)
        # keep track of sequence count after each pcr cycle (except last one)
        seqPop = np.zeros(pcrCycleNum)
        # for each seq in the mutation pool
        mutatedPool = np.zeros(self.seqLength, dtype=np.int)
        for si, (seqIdx, sc) in enumerate(zip(prevSeqs, prevCopies)):
            sn = sc
            # random PCR with bias using brute force
            for n in range(pcrCycleNum):
                # sequence count after n cycles
                seqPop[n] = sn
                # amplify count using initial count, polymerase yield, and bias score
                sn += int(binom(sn, min(0.99999, pcrYld+amplfdSeqs[seqIdx][2])))
            amplfdSeqs[seqIdx][0] = sn
            # compute cycle number probabilities
            # grab probabilities to draw it after each pcr cycle
            cycleNumProbs = seqPop / seqPop.sum()
            # if accumulated seq count is greater than 10,000
            if np.sum(seqPop) > 10000:
                # for each possible number of mutations in any seq copy (1-self.seqLength)
                # approximate the proportion of copies that will be mutated using
                # corresponding probability p(M=mutNum)
                mutatedPool = mutNumProbs[1:self.seqLength+1]*seqPop.sum()
            # if seq count is less than 10,000
            else:
                # draw random mutNum from the mutation distribution for each seq copy
                # poisson call returns mostly 0, should be optimisable
                muts = poisson(self.errorRate*self.seqLength, int(np.sum(seqPop)))  # SLOW STEP
                # remove all drawn numbers equal to zero
                muts = muts[muts != 0]
                # for each non-zero mutation number
                for mutNum in muts:
                    # increment copy number to be mutated
                    mutatedPool[mutNum] += 1

            if mutatedPool.sum() == 0:
                continue
            # for each mutation instance for the seq
            for mutNum, mutFreq in enumerate(mutatedPool):
                mutFreq = int(mutatedPool[mutNum])
                # if the mutation is carried out on less than 10,000 copies, draw random numbers...:(
                if mutFreq == 0:
                    continue
                elif mutFreq < 10000:
                    # compute a discrete distribution from probabilities
                    # draw random cycle numbers after which the sequences were drawn for mutation
                    cycleNums = random.choice(np.arange(pcrCycleNum), p=cycleNumProbs, size=mutFreq)
                    # generate the wild-type sequence string
                    wildTypeSeq = apt.pseudoAptamerGenerator(seqIdx)
                    # for each copy to be mutated
                    for mut in range(mutFreq):
                        # draw random positions on the seq to mutate
                        randPos = random.randint(1, self.seqLength+1, size=mutNum+1)
                        # draw a random nucleotide for each position
                        randNucs = random.randint(apt.La, size=mutNum+1)
                        mutatedSeq = wildTypeSeq
                        # for each position in seq, replace with random nucleotide
                        for posNum, pos in enumerate(randPos):
                            mutatedSeq = mutatedSeq[:(pos-1)] + apt.alphabetSet[randNucs[posNum]] + \
                                         mutatedSeq[pos:]
                        # generate index of mutant based on string
                        mutatedSeqIdx = apt.pseudoAptamerIndexGenerator(mutatedSeq)
                        # if mutant not found in amplified pool
                        if mutatedSeqIdx not in amplfdSeqs:
                            # add seq and its info to the amplified pool
                            mutDist = md(mutatedSeq)
                            mutBias = d.bias_func(mutatedSeq, self.seqLength)
                            amplfdSeqs[mutatedSeqIdx] = np.array([1, mutDist, mutBias])
                        wildTypeCount = 1
                        mutantCount = 1
                        # mutantNum = (1+pcrYld)**(pcrCycleNum - cycleNums[mut])
                        # for each pcr cycle after mutation has occured
                        for n in range(pcrCycleNum-cycleNums[mut]):
                            # compute amplified mutant count
                            mutantCount += int(binom(mutantCount,
                                               min(0.99999, pcrYld+amplfdSeqs[mutatedSeqIdx][2])))
                            # compute loss of count from wild-type
                            wildTypeCount += int(binom(wildTypeCount,
                                                 min(0.99999, pcrYld+amplfdSeqs[seqIdx][2])))
                        # increment mutant seq count in amplified pool
                        amplfdSeqs[mutatedSeqIdx][0] += mutantCount
                        # decrement wild-type seq count in amplfied pool
                        amplfdSeqs[seqIdx][0] -= wildTypeCount
                # if mutation carried out on more than 10,000 copies, avoid drawing random nums
                elif mutFreq > 10000:
                    # calculate fraction of mutants for each possible mutation
                    initialMutCount = int(0.333*mutFreq/self.seqLength)
                    # for each possible position that mutation can occur
                    for seqPos in range(self.seqLength):
                        # grab the sequence encoding array
                        seqArray = apt.get_seqArray(seqIdx)
                        # original nucleotide index
                        oni = seqArray[seqPos]
                        # mutated nucleotide index
                        for mni in range(4):
                            # skip if same residue
                            if mni == oni:
                                continue
                            mnd = mni-oni
                            mutatedSeqIdx = seqIdx+(4**(self.seqLength-seqPos-1)*mnd)
                            # if the mutated seq is not found in amplified pool
                            if mutatedSeqIdx not in amplfdSeqs:
                                # generate seq string using its index
                                mutatedSeq = apt.pseudoAptamerGenerator(mutatedSeqIdx)
                                mutDist = md(mutatedSeq)
                                # compute bias score of seq
                                mutBias = d.bias_func(mutatedSeq, self.seqLength)
                                # add to amplified pool
                                amplfdSeqs[mutatedSeqIdx] = np.array([0, mutDist, mutBias])
                            for cycleNum, cycleNumProb in enumerate(cycleNumProbs):
                                # compute expected number of mutant copies after amplification
                                amplfdSeqs[mutatedSeqIdx][0] += int(cycleNumProb *
                                                                    initialMutCount *
                                                                    (1+pcrYld)**(pcrCycleNum-cycleNum))
                                # compute expected decrease in no. of wild type seq
                                amplfdSeqs[seqIdx][0] -= int(cycleNumProb*initialMutCount *
                                                             (1+pcrYld)**(pcrCycleNum-cycleNum))
            if int(Lc/20) == 0 or si % int(Lc/20) == 0:
                print("Mutated {:6.2f}%".format(100.0*si/Lc))
        print("Mutation has been carried out")
        return amplfdSeqs
