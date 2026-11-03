// DV2-MAX x SP59 (2026-11-02) hard gate: call the C++ bridge WCPPyUtil::DV2_Vertex
// (the exact function determine_overall_main_vertex_DL calls) on a synthetic
// 2-prong cloud and print the returned [x, y, z, score].  Proves: embedded Python
// starts, DV2_Vertex.py + dv2max_vertexer import, the bundle loads, a point comes back.
#include "WCPPyUtil/DV2_Vertex.h"

#include <cmath>
#include <cstdio>
#include <random>
#include <vector>

int main(int argc, char** argv)
{
    if (argc < 2) { std::fprintf(stderr, "usage: %s bundle.json\n", argv[0]); return 2; }
    std::vector<std::vector<float>> in(4);
    auto push = [&](double x, double y, double z, double q) {
        in[0].push_back(x); in[1].push_back(y); in[2].push_back(z); in[3].push_back(q);
    };
    const double vx = -100, vy = 0, vz = 200;
    push(vx, vy, vz, 0);            // PR-graph vertex rows first
    push(vx, vy, vz + 40, 0);
    for (int i = 0; i < 200; ++i) { const double t = 40.0 * i / 199; push(vx + 0.3 * t, vy + 0.2 * t, vz + 0.93 * t, 1000); }
    std::mt19937 rng(1); std::normal_distribution<double> g(0, 3);
    for (int i = 0; i < 300; ++i) push(vx + 5 + g(rng), vy - 10 + g(rng), vz + 30 + g(rng), 600);
    std::vector<float> trad{-100.f, 0.f, 240.f};
    auto out = WCPPyUtil::DV2_Vertex("DV2_Vertex", "DV2_Vertex", argv[1], in, 2, trad, 0.1, -1000.0, "float32");
    std::printf("DV2_CXX_SMOKE n_out=%zu", out.size());
    for (auto v : out) std::printf(" %.4f", v);
    std::printf("\n");
    if (out.size() != 4) { std::printf("DV2_CXX_SMOKE_FAIL\n"); return 1; }
    const double d = std::sqrt(std::pow(out[0] - vx, 2) + std::pow(out[1] - vy, 2) + std::pow(out[2] - vz, 2));
    std::printf("DV2_CXX_SMOKE distance_to_planted_vertex_cm=%.3f\n", d);
    std::printf("DV2_CXX_SMOKE_PASS\n");
    return 0;
}
