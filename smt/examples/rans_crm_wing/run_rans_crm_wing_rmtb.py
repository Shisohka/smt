from smt.examples.rans_crm_wing.rans_crm_wing import (
    get_rans_crm_wing,
    plot_rans_crm_wing,
)
from smt.surrogate_models import RMTB

xt, yt, xlimits = get_rans_crm_wing()

interp = RMTB(
    num_ctrl_pts=20, xlimits=xlimits, nonlinear_maxiter=100, energy_weight=1e-12
)
interp.set_training_values(xt, yt)
interp.train()

plot_rans_crm_wing(xt, yt, xlimits, interp)
