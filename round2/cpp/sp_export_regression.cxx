// C++ regression fixture for the SP BDT exporter (round2/sp_retrain/export_tmva.py).
//
//   sp_export_regression <model.xml> <names.txt> <rows.csv> <out.csv>
//
// names.txt: one input name per line, in XML <Variables> order. rows.csv: one row per line, comma-separated float
// values (Python writes them with %.9g, so text -> float32 is exact). For every row it evaluates
//   (1) TMVA::Reader::EvaluateMVA with Float_t bindings (the MicroBooNE / SBND scorer pattern), and
//   (2) the Wire-Cell toolkit's WireCell::Root::TmvaGradForest::evaluate (fast reader used in production),
// and writes "row,reader,forest" with %.17g. Python compares both with sp_retrain.tmva_grad.GradForest and the native
// XGBoost margin. A swapped-names check runs once: TmvaGradForest must refuse a wrong variable order.
// Development fixtures only (DEV_DO_NOT_DEPLOY models).
#include "TMVA/Reader.h"
#include "WireCellRoot/TmvaGradForest.h"

#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

int main(int argc, char** argv)
{
    if (argc != 5) { std::cerr << "usage: sp_export_regression model.xml names.txt rows.csv out.csv\n"; return 2; }
    std::vector<std::string> names;
    { std::ifstream f(argv[2]); std::string s; while (std::getline(f, s)) if (!s.empty()) names.push_back(s); }
    std::vector<float> vars(names.size(), 0.f);
    TMVA::Reader reader("!Color:Silent");
    for (size_t i = 0; i < names.size(); ++i) reader.AddVariable(names[i].c_str(), &vars[i]);
    reader.BookMVA("BDT", argv[1]);
    WireCell::Root::TmvaGradForest forest;
    forest.load(argv[1], names);
    int refused = 0;
    if (names.size() > 1) {
        auto swapped = names; std::swap(swapped[0], swapped[1]);
        WireCell::Root::TmvaGradForest bad;
        try { bad.load(argv[1], swapped); } catch (...) { refused = 1; }
    }
    std::ifstream rows(argv[3]);
    FILE* out = std::fopen(argv[4], "w");
    std::fprintf(out, "row,reader,forest\n");
    std::string line; long n = 0;
    while (std::getline(rows, line)) {
        if (line.empty()) continue;
        std::stringstream ss(line); std::string tok; size_t j = 0;
        while (std::getline(ss, tok, ',') && j < vars.size()) vars[j++] = std::stof(tok);
        if (j != vars.size()) { std::cerr << "row " << n << ": " << j << " values\n"; return 3; }
        const double r = reader.EvaluateMVA("BDT");
        const double g = forest.evaluate(vars.data());
        std::fprintf(out, "%ld,%.17g,%.17g\n", n, r, g);
        ++n;
    }
    std::fclose(out);
    std::printf("SP_EXPORT_REGRESSION rows=%ld nvars=%zu ntrees=%zu swapped_names_refused=%d\n", n, names.size(), forest.ntrees(), refused);
    return 0;
}
