import torch
from torch import nn

from torch_geometric.utils import coalesce


class ARRWPLinearNodeEncoder(nn.Module):
    """
    FC_1(ARRWP) + FC_2 (node_attr)
    note: FC_2 is supposed to be applied
    """

    def __init__(
        self, in_dim, emb_dim,
        norm_type=None, use_bias=False,
        mx_name="arrwp",
    ):
        super().__init__()

        self.mx_name = mx_name

        self.fc = nn.Linear(in_dim, emb_dim, bias=use_bias)
        torch.nn.init.xavier_uniform_(self.fc.weight)

        if norm_type == "batchnorm":
            self.norm = nn.BatchNorm1d(emb_dim)
        elif norm_type == "layernorm":
            self.norm = nn.LayerNorm(emb_dim)
        else:
            self.norm = None

    def forward(self, batch):
        arrwp = batch[f"node_{self.mx_name}"]
        arrwp = self.fc(arrwp)

        if "x" in batch:
            batch.x = batch.x + arrwp
        else:
            batch.x = arrwp

        if self.norm:
            arrwp = self.norm(arrwp)

        return batch
    

class ARRWPLinearEdgeEncoder(torch.nn.Module):
    """
    FC_1(ARRWP) + FC_2(edge_attr)
    notes:
        - Batchnorm/Layernorm might ruin some properties of
        encoding on providing shortest-path distance info
        - FC_2 is supposed to be applied
    """

    def __init__(
        self, in_dim, emb_dim,
        norm_type=None, use_bias=False,
        mx_name="arrwp",
    ):
        super().__init__()

        self.mx_name = mx_name

        self.fc = nn.Linear(in_dim, emb_dim, bias=use_bias)
        torch.nn.init.xavier_uniform_(self.fc.weight)

        if norm_type == "batchnorm":
            self.norm = nn.BatchNorm1d(emb_dim)
        elif norm_type == "layernorm":
            self.norm = nn.LayerNorm(emb_dim)
        else:
            self.norm = None

    def forward(self, batch):
        arrwp_index = batch[f"edge_{self.mx_name}_index"]
        arrwp_val = batch[f"edge_{self.mx_name}_val"]
        edge_index = batch.edge_index
        edge_attr = batch.edge_attr
        
        arrwp_val = self.fc(arrwp_val)

        if edge_attr is None:
            edge_attr = edge_index.new_zeros(
                edge_index.size(1), arrwp_val.size(1),
            )

        upd_edge_index, upd_edge_attr = coalesce(
            torch.cat([edge_index, arrwp_index], dim=1),
            torch.cat([edge_attr, arrwp_val], dim=0),
            reduce="add",
        )

        if self.norm:
            upd_edge_attr = self.norm(upd_edge_attr)

        batch.edge_index, batch.edge_attr =\
            upd_edge_index, upd_edge_attr
        return batch