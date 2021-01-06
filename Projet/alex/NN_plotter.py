# -*- coding: utf-8 -*-
"""
Created on Wed Jan  6 20:29:27 2021

@author: ewenf
"""

from __future__ import print_function
import tensorflow as tf
import keras,sklearn
import matplotlib.pyplot as plt
import pickle
import numpy as np


# suppress tensorflow compilation warnings
import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
seed=0
np.random.seed(seed) # fix random seed

from keras.models import Sequential
from keras.layers import Dense, Dropout, Flatten

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, MaxAbsScaler, MinMaxScaler

from dscribe.descriptors import SOAP
from ase.build import molecule
from ase import Atoms
from keras.models import load_model

datapath='../../../'
#positions and corresponding energies of a zundel molecule importation
all_positions = pickle.load(open(os.path.join(datapath,'zundel_100K_pos'),'rb'))
all_energies = pickle.load(open(os.path.join(datapath,'zundel_100K_energy'),'rb'))[1:]



#parameters settings

molecule_params={
        'n_elements': 2,
        'n_oxygens': 2,
        'n_hydrogens': 5,
        'molecules_order':[8,8,1,1,1,1,1]
 
       
    
    }


dscribe_params={
        'nmax': 4,
        'lmax': 5,
        'rcut': 11.0,
        'sigma_SOAP': 1.0,
        'periodic': False,
        'species': ["H","O"],
        'sparse':False,
 
       
    
    }

model_params={
        'layers_units': 30,
        'layers_number': 2,
        'kernel_initializer': None,
 
       
    
    }


data_params={
        'slicing': 5,
        'train_ratio':0.85,
        'val_ratio':0.1,
  
 
       
    
    }

PCA_params={
        'Scaler_Pre_PCA': StandardScaler(),
        'Scaler_Post_PCA':StandardScaler(),
        'pca_pourcentage':0.999999,
  
 
       
    
    }


fit_params={
        'epochs': 500,
        'batch_size':30,
        'verbose':1,
  
 
       
    
    }


#data_slicing
positions = all_positions[::data_params['slicing']]
energies = all_energies[::data_params['slicing']]


#soap descriptors
soap = SOAP(nmax=dscribe_params['nmax'],
            lmax=dscribe_params['lmax'],
            rcut=dscribe_params['rcut'],
            sigma=dscribe_params['sigma_SOAP'],
            periodic=dscribe_params['periodic'],
            species=dscribe_params['species'],
            sparse=dscribe_params['sparse'],
            
)

n_configs = np.shape(positions)[0]
n_features = soap.get_number_of_features()
n_dims = n_features

n_atoms = molecule_params['n_hydrogens'] + molecule_params['n_oxygens']


#zundel molecule creation
zundels = np.empty(n_configs,dtype=object )
for i_configs in range(n_configs):
      zundels[i_configs] = Atoms(numbers=molecule_params['molecules_order'], positions=positions[i_configs])


# computing descriptors for each positions
descriptors=np.empty([n_configs,n_atoms,n_features])
for i_configs in range(n_configs):
    descriptors[i_configs,:,:] = soap.create(zundels[i_configs],positions=np.arange(n_atoms),n_jobs=4)
print('soap ok')

#scaling inputs and outputs
energies_scaler = StandardScaler().fit(energies.reshape((-1,1))) 
scaled_energies = energies_scaler.transform(energies.reshape((-1,1)))



n_features_oxygens = n_configs*molecule_params['n_oxygens']
n_features_hydrogens = n_configs*molecule_params['n_hydrogens']


scaled_descriptors = np.empty([n_features_hydrogens+n_features_oxygens,n_dims])


scaler_O_1 = PCA_params['Scaler_Pre_PCA']
scaler_H_1 = PCA_params['Scaler_Pre_PCA']
scaled_descriptors[n_features_oxygens:,:] = scaler_H_1.fit_transform(descriptors.reshape(n_features_hydrogens+n_features_oxygens,n_dims)[n_features_oxygens:,:])
scaled_descriptors[:n_features_oxygens,:] = scaler_O_1.fit_transform(descriptors.reshape(n_features_hydrogens+n_features_oxygens,n_dims)[:n_features_oxygens,:])



#PCA


var_ratio_pca_oxygens = np.empty(n_features_oxygens)
var_ratio_pca_hydrogens = np.empty(n_features_hydrogens)   

pca_oxygens = PCA(n_dims)
pca_hydrogens = PCA(n_dims)
pca_oxygens.fit(scaled_descriptors[:n_features_oxygens,:])
pca_hydrogens.fit(scaled_descriptors[n_features_oxygens:,:])
var_ratio_pca_hydrogens = pca_hydrogens.explained_variance_ratio_
var_ratio_pca_oxygens = pca_oxygens.explained_variance_ratio_

var_ratio_oxygens = 0
var_ratio_hydrogens = 0
pca_treshold_hydrogens = 0
pca_treshold_oxygens = 0

while var_ratio_hydrogens<PCA_params['pca_pourcentage']:
    var_ratio_hydrogens +=  var_ratio_pca_hydrogens[pca_treshold_hydrogens]
    pca_treshold_hydrogens += 1
    
while var_ratio_oxygens<PCA_params['pca_pourcentage']:
    var_ratio_oxygens += var_ratio_pca_oxygens[pca_treshold_oxygens]
    pca_treshold_oxygens += 1
        

pca_treshold = max(pca_treshold_hydrogens,pca_treshold_oxygens)
print("dimension desc post pca=", pca_treshold, "\n"
      "dimennsion desc pre pca=",n_dims)

scaled_pca_descriptors = np.empty([n_configs,n_atoms,n_dims])
for i_hydrogens in range(molecule_params['n_hydrogens'] ):
    scaled_pca_descriptors[:,i_hydrogens+molecule_params['n_oxygens'],:] = pca_hydrogens.transform(scaled_descriptors.reshape(n_configs,n_atoms,n_dims)[:,i_hydrogens+molecule_params['n_oxygens'],:])
for i_oxygens in range(molecule_params['n_oxygens']):
    scaled_pca_descriptors[:,i_oxygens,:] = pca_oxygens.transform(scaled_descriptors.reshape(n_configs,n_atoms,n_dims)[:,i_oxygens,:])
    
#scaling post pca



scaler_O_2 = PCA_params['Scaler_Post_PCA']
scaler_H_2 = PCA_params['Scaler_Post_PCA']

scaled_pca_descriptors.reshape(n_features_hydrogens+n_features_oxygens,n_dims)[n_features_oxygens:,:pca_treshold] = scaler_H_2.fit_transform(scaled_descriptors.reshape(n_features_hydrogens+n_features_oxygens,n_dims)[n_features_oxygens:,:pca_treshold])
scaled_pca_descriptors.reshape(n_features_hydrogens+n_features_oxygens,n_dims)[:n_features_oxygens,:pca_treshold] = scaler_O_2.fit_transform(scaled_descriptors.reshape(n_features_hydrogens+n_features_oxygens,n_dims)[:n_features_oxygens,:pca_treshold])

#swaping axes for NN purpose
descriptors_swap = np.swapaxes(scaled_pca_descriptors.reshape(n_configs,n_atoms,n_dims)[:,:,:pca_treshold],0,1)

train_limit=int(data_params['train_ratio']*n_configs)
val_limit=int((data_params['train_ratio']+data_params['val_ratio'])*n_configs)


#setting the train and test and validation set
descriptors_train = descriptors_swap[:,:train_limit,:]
descriptors_val = descriptors_swap[:,train_limit:val_limit,:]
descriptors_test = descriptors_swap[:,val_limit:,:]
energies_train = scaled_energies[:train_limit]
energies_val = scaled_energies[train_limit:val_limit]
energies_test = scaled_energies[val_limit:]


#creating a list of array to fit in the NN
descriptors_train_nn = []
descriptors_test_nn = []
descriptors_val_nn = []
for i_atom in range(n_atoms):
    descriptors_train_nn.append(descriptors_train[i_atom,:,:])
    descriptors_test_nn.append(descriptors_test[i_atom,:,:])
    descriptors_val_nn.append(descriptors_val[i_atom,:,:])

Zundel_NN = load_model('Fitted_Zundel_NN.h5')
Zundel_NN.summary()
#descaling energies and outputs
predicted_energies = Zundel_NN.predict(descriptors_test_nn)
descaled_energies = energies_scaler.inverse_transform(scaled_energies)
descaled_predicted_energies = energies_scaler.inverse_transform(predicted_energies)
energy = np.linspace(0,0.008,200)
print("mean error=",np.mean(np.absolute(descaled_energies[val_limit:]-descaled_predicted_energies)))

plt.figure(figsize=[7,7])
plt.plot(descaled_energies[val_limit:],descaled_predicted_energies,'.',markersize=2)
plt.plot(energy,energy,markersize=2,color='red')
plt.xlabel('True Energies (en Hartree)')
plt.ylabel('Predicted Energies (en Hartree)')
plt.legend(['Predicted Energy'], loc='best')
plt.savefig('comparaison.jpg')