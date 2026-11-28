// TMVA::Reader evaluation of one upstream Wire-Cell level-1 weight file on many objects (development check).
//
//   upstream_l1_tmva_eval <model.xml> <names.txt> <X.f32> <nrows> <out.f64>
//
// names.txt: the input names in the XML <Variables> order (the toolkit binds them in that order). X.f32: nrows x nvar
// row-major float32 (NaN kept: TMVA::Reader returns -999 for a NaN input, as in the chain). out.f64: nrows doubles,
// EvaluateMVA("MyBDT") -- the value UbooneNumuBDTScorer / UbooneNueBDTScorer narrow to float and pool.
// Used for the SHIPPED small models (TMVA AdaBoost with VarTransform D,P,U,G,D,N), which the numpy evaluator does not
// implement, and as an arithmetic cross-check of the released (Grad) chain files.
#include "TMVA/Reader.h"

#include <cstdio>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char** argv)
{
    if (argc != 6) { std::cerr << "usage: upstream_l1_tmva_eval model.xml names.txt X.f32 nrows out.f64\n"; return 2; }
    std::vector<std::string> names;
    { std::ifstream f(argv[2]); std::string s; while (std::getline(f, s)) if (!s.empty()) names.push_back(s); }
    const long nrows = std::stol(argv[4]);
    const size_t nv = names.size();
    std::vector<float> vars(nv, 0.f);
    TMVA::Reader reader("!Color:Silent");
    for (size_t i = 0; i < nv; ++i) reader.AddVariable(names[i].c_str(), &vars[i]);
    reader.BookMVA("MyBDT", argv[1]);
    FILE* in = std::fopen(argv[3], "rb");
    FILE* out = std::fopen(argv[5], "wb");
    if (!in || !out) { std::cerr << "cannot open input/output\n"; return 3; }
    std::vector<float> row(nv);
    long n = 0;
    for (; n < nrows; ++n) {
        if (std::fread(row.data(), sizeof(float), nv, in) != nv) { std::cerr << "short read at row " << n << "\n"; return 4; }
        for (size_t j = 0; j < nv; ++j) vars[j] = row[j];
        const double v = reader.EvaluateMVA("MyBDT");
        std::fwrite(&v, sizeof(double), 1, out);
    }
    std::fclose(in); std::fclose(out);
    std::printf("UPSTREAM_L1_TMVA_EVAL rows=%ld nvars=%zu xml=%s\n", n, nv, argv[1]);
    return 0;
}
