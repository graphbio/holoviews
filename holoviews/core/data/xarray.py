from __future__ import absolute_import

import numpy as np
import xarray as xr

from ..ndmapping import item_check, sorted_context
from .. import ViewableElement, Element, NdMapping, util
from .interface import Interface


class XArrayInterface(Interface):

    types = (xr.Dataset if xr else None,)

    datatype = 'xarray'

    @classmethod
    def dimension_type(cls, dataset, dim):
        name = dataset.get_dimension(dim).name
        idx = list(dataset.data.keys()).index(name)
        return dataset.data[name].dtype.type


    @classmethod
    def dtype(cls, dataset, dim):
        name = dataset.get_dimension(dim).name
        idx = list(dataset.data.keys()).index(name)
        return dataset.data[name].dtype


    @classmethod
    def init(cls, eltype, data, kdims, vdims):
        element_params = eltype.params()
        kdim_param = element_params['kdims']
        vdim_param = element_params['vdims']

        if isinstance(data, xr.Dataset):
            if vdims is None:
                vdims = list(data.data_vars.keys())
            if kdims is None:
                kdims = list(data.dims.keys())
        return data, {'kdims': kdims, 'vdims': vdims}, {}


    @classmethod
    def range(cls, dataset, dimension):
        dim = dataset.get_dimension(dimension).name
        if dim in dataset.data:
            data = dataset.data[dim].data
            return data.min(), data.max()
        else:
            return np.NaN, np.NaN


    @classmethod
    def groupby(cls, dataset, dimensions, container_type, group_type, **kwargs):
        index_dims = [dataset.get_dimension(d) for d in dimensions]
        element_dims = [kdim for kdim in dataset.kdims
                        if kdim not in index_dims]

        group_kwargs = {}
        if group_type != 'raw' and issubclass(group_type, Element):
            group_kwargs = dict(util.get_param_values(dataset),
                                kdims=element_dims)
        group_kwargs.update(kwargs)
        
        # XArray 0.7.2 does not support multi-dimensional groupby
        # Replace custom implementation when 
        # https://github.com/pydata/xarray/pull/818 is merged.
        if len(dimensions) == 1:
            data = [(k, group_type(v, **group_kwargs)) for k, v in
                    dataset.data.groupby(dimensions[0])]
        else:
            unique_iters = [cls.values(dataset, d, False) for d in dimensions]
            indexes = zip(*[vals.flat for vals in util.cartesian_product(unique_iters)])
            data = [(k, group_type(dataset.data.sel(**dict(zip(dimensions, k)))))
                    for k in indexes]

        if issubclass(container_type, NdMapping):
            with item_check(False), sorted_context(False):
                return container_type(data, kdims=index_dims)
        else:
            return container_type(data)


    @classmethod
    def values(cls, dataset, dim, expanded=True, flat=True):
        data = dataset.data[dim].data
        if dim in dataset.vdims:
            if data.ndim == 1:
                return np.array(data)
            else:
                data = np.rot90(data)
                return data.flatten() if flat else data
        elif not expanded:
            return data
        else:
            arrays = [dataset.data[d.name].data for d in dataset.kdims]
            product = util.cartesian_product(arrays)[dataset.get_dimension_index(dim)]
            return product.flatten() if flat else product


    @classmethod
    def aggregate(cls, dataset, dimensions, function, **kwargs):
        if len(dimensions) > 2:
            raise NotImplementedError('Multi-dimensional aggregation not '
                                      'supported as of xarray <=0.7.2.')
        return dataset.data.groupby(dimensions).apply(function)


    @classmethod
    def concat(cls, dataset_objs):
        #cast_objs = cls.cast(dataset_objs)
        # Reimplement concat to automatically add dimensions
        # once multi-dimensional concat has been added to xarray.
        return xr.concat([col.data for col in dataset_objs], dim='concat_dim')


    @classmethod
    def reindex(cls, dataset, kdims=None, vdims=None):
        # DataFrame based tables don't need to be reindexed
        return dataset.data

    @classmethod
    def sort(cls, dataset, by=[]):
        return dataset

    @classmethod
    def select(cls, dataset, selection_mask=None, **selection):
        selection = {k: list(v) if isinstance(v, set) else v
                     for k, v in selection.items()}
        return dataset.data.sel(**selection)

    @classmethod
    def length(cls, dataset):
        return np.product(dataset[dataset.vdims[0].name].shape)
    
    @classmethod
    def dframe(cls, dataset, dimensions):
        if dimensions:
            return dataset.reindex(columns=dimensions)
        else:
            return dataset.data.to_dataframe().reset_index(dimensions)

    @classmethod
    def sample(cls, columns, samples=[]):
        raise NotImplementedError

    @classmethod
    def add_dimension(cls, columns, dimension, dim_pos, values, vdim):
        raise NotImplementedError

        
Interface.register(XArrayInterface)
