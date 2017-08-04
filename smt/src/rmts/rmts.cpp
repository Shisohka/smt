#include "rmts.hpp"
#include <assert.h>
#include <math.h>
#include <iostream>

using namespace std;

RMTS::RMTS() {
  lower = NULL;
  upper = NULL;
}

RMTS::~RMTS() {
  delete[] lower;
  delete[] upper;
}

void RMTS::setup(int nx, double * lower, double * upper) {
  this->nx = nx;
  this->lower = new double[nx];
  this->upper = new double[nx];

  memcpy(this->lower, lower, nx * sizeof(*lower));
  memcpy(this->upper, upper, nx * sizeof(*upper));
}

// void RMTS::compute_jac(int n, double* x, double* jac) {
//   double w[nt], r2[nt], min_val, sum, d;
//   int min_loc;
//
//   for (int i = 0; i < n; i++) {
//     min_val = 1.;
//     min_loc = 0;
//     for (int it = 0; it < nt; it++) {
//       r2[it] = 0.;
//       for (int ix = 0; ix < nx; ix++) {
//         d = x[i * nx + ix] - xt[it * nx + ix];
//         r2[it] += pow(d, 2);
//       }
//       if (r2[it] < min_val) {
//         min_val = r2[it];
//         min_loc = it;
//       }
//       w[it] = pow(r2[it], -p / 2.);
//     }
//
//     if (min_val == 0.) {
//       for (int it = 0; it < nt; it++) {
//         jac[i * nt + it] = 0.;
//       }
//       jac[i * nt + min_loc] = 1.;
//     }
//     else {
//       sum = 0;
//       for (int it = 0; it < nt; it++) {
//         sum += w[it];
//       }
//       for (int it = 0; it < nt; it++) {
//         jac[i * nt + it] = w[it] / sum;
//       }
//     }
//   }
// }
