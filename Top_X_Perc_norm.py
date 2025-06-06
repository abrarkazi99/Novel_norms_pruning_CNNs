import torch
import torch.nn.utils.prune as prune

class TopXPercStructured(prune.BasePruningMethod):

    PRUNING_TYPE = "structured"

    def __init__(self, amount, x, dim=-1):
        prune._validate_pruning_amount_init(amount)
        self.amount = amount
        self.x = x
        self.dim = dim

    def compute_mask(self, t, default_mask):
        prune._validate_structured_pruning(t)
        prune._validate_pruning_dim(t, self.dim)

        tensor_size = t.shape[self.dim]
        nparams_toprune = prune._compute_nparams_toprune(self.amount, tensor_size)
        nparams_tokeep = tensor_size - nparams_toprune
        prune._validate_pruning_amount(nparams_toprune, tensor_size)

        norm = compute_top_x_perc_norm(t, self.x)
        topk = torch.topk(norm, k=nparams_tokeep, largest=True)

        def make_mask(t, dim, indices):
            mask = torch.zeros_like(t)
            slc = [slice(None)] * len(t.shape)
            slc[dim] = indices
            mask[slc] = 1
            return mask

        if nparams_toprune == 0:
            mask = default_mask
        else:
            mask = make_mask(t, self.dim, topk.indices)
            mask *= default_mask.to(dtype=mask.dtype)

        return mask

    @classmethod
    def apply(cls, module, name, amount, x, importance_scores=None):

        return super().apply(
            module,
            name,
            amount=amount,
            x=x,
            dim=0,
            importance_scores=importance_scores,
        )

def top_x_perc_structured(module, name, amount, x, importance_scores=None):
    TopXPercStructured.apply(
        module, name, amount, x, importance_scores=importance_scores
    )
    return module

def compute_top_x_perc_norm(t, x):
    weights_flattened_abs = torch.abs(torch.flatten(t,start_dim=1,end_dim=3))
    weights_per_filter=len(weights_flattened_abs[0])
    num_weights_retain = round(weights_per_filter*x/100)
    weights_sorted, _ = torch.sort(weights_flattened_abs,descending=True)
    top_weights = weights_sorted[:,:num_weights_retain]
    norms = torch.sum(top_weights,dim=1)
    return norms
