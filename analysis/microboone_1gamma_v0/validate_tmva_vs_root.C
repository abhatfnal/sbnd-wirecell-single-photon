// validate_tmva_vs_root.C
// ROOT TMVA validation macro for single_photon numu BDT on evt_0001.
// Run inside the sbndcode container after sourcing larsoft env.
//
// Expected numu score (Python evaluator): 2.9059670495
//
// Usage: root -q -l validate_tmva_vs_root.C

#include "TMVA/Reader.h"
#include "TFile.h"
#include "TTree.h"
#include <iostream>
#include <vector>

void validate_tmva_vs_root() {
    const char* xml_path = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/reference"
                           "/sbnd_single_photon_microboone_reference_20261005/weights"
                           "/single_photon_numu_bdt_final.xml";
    const char* root_path = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0"
                            "/ncdelta_50evt/wirecell/evt_0001/tracking-pr.root";

    TMVA::Reader reader("Silent");

    // Variable list (73 in XML order)
    // These must match the order in single_photon_numu_bdt_final.xml
    std::vector<std::string> var_names = {
        "numu_cc_flag_3","numu_cc_3_particle_type","numu_cc_3_max_length","numu_cc_3_track_length",
        "numu_cc_3_max_length_all","numu_cc_3_max_muon_length","numu_cc_3_n_daughter_tracks",
        "numu_cc_3_n_daughter_all","shw_sp_br1_1_shower_type","shw_sp_br1_1_vtx_n_segs",
        "shw_sp_br1_1_n_shower_segs","shw_sp_br1_1_flag_sg_topology","shw_sp_br1_1_flag_sg_trajectory",
        "shw_sp_br1_1_sg_length","shw_sp_br1_2_n_shower_main_segs","shw_sp_br1_2_max_dev",
        "shw_sp_br2_1_n_shower_all","shw_sp_br2_1_flag_sg_topology","shw_sp_br2_2_n_shower_all",
        "shw_sp_br2_2_flag_sg_topology","shw_sp_br3_1_n_shower_segs","shw_sp_br3_2_n_shower_segs",
        "shw_sp_br3_3_n_shower_segs","shw_sp_br3_4_n_shower_segs","shw_sp_br3_5_v_larl_pca",
        "shw_sp_br3_5_v_angle","shw_sp_br3_5_v_sg_length","shw_sp_br3_6_n_shower_segs",
        "shw_sp_br3_7_sg_length","shw_sp_br3_8_max_dQ_dx","shw_sp_br3_8_n_main_segs",
        "shw_sp_br3_8_sg_length","shw_sp_br4_1_n_shower_segs","shw_sp_br4_2_ratio_45",
        "shw_sp_br4_2_ratio_35","shw_sp_br4_2_ratio_25","shw_sp_br4_2_ratio_15",
        "shw_sp_br4_2_ratio","shw_sp_br4_2_n_shower_segs","shw_sp_lol_1_v_flag",
        "shw_sp_lol_1_v_energy","shw_sp_lol_1_v_vtx_n_segs","shw_sp_lol_1_v_nseg",
        "shw_sp_lol_1_v_angle","shw_sp_lol_2_v_flag","shw_sp_lol_2_v_length",
        "shw_sp_lol_2_v_angle","shw_sp_lol_2_v_type","shw_sp_lol_3_flag_match",
        "shw_sp_lol_3_angle","shw_sp_lol_3_n_valid_tracks","shw_sp_lol_3_min_angle",
        "shw_sp_lol_3_vtx_n_segs","shw_sp_lol_3_min_count","shw_sp_lol_3_pt_fraction",
        "shw_sp_lol_3_sg_length","shw_sp_hol_1_lol_flag","shw_sp_hol_1_min_angle",
        "shw_sp_hol_1_energy","shw_sp_hol_1_vangle","shw_sp_hol_2_lol_flag",
        "shw_sp_hol_2_min_angle","shw_sp_hol_2_medium_dQ_dx","shw_sp_hol_2_ncount",
        "shw_sp_hol_2_energy","shw_sp_n_20mev_showers","shw_sp_n_br4_showers",
        "shw_sp_n_20br1_showers","shw_sp_shw_vtx_dis","shw_sp_max_shw_dis",
        "numu_1_score","numu_score"
    };

    std::vector<float> var_vals(var_names.size(), 0.0f);
    for (size_t i = 0; i < var_names.size(); i++) {
        reader.AddVariable(var_names[i].c_str(), &var_vals[i]);
    }

    reader.BookMVA("BDT", xml_path);

    // Read the event from tracking-pr.root
    TFile* f = TFile::Open(root_path, "READ");
    TTree* tt = (TTree*)f->Get("T_tagger");

    std::vector<float*> branch_ptrs(var_names.size(), nullptr);
    for (size_t i = 0; i < var_names.size(); i++) {
        branch_ptrs[i] = new float(0.0f);
        tt->SetBranchAddress(var_names[i].c_str(), branch_ptrs[i]);
    }
    tt->GetEntry(0);

    for (size_t i = 0; i < var_names.size(); i++) {
        var_vals[i] = *branch_ptrs[i];
    }

    float score = reader.EvaluateMVA("BDT");

    std::cout << "=== ROOT TMVA Validation ===" << std::endl;
    std::cout << "evt_0001 numu BDT score (ROOT TMVA): " << std::fixed << std::setprecision(8) << score << std::endl;
    std::cout << "Expected (Python evaluator):           2.90596705" << std::endl;
    float diff = std::abs(score - 2.90596705f);
    std::cout << "Absolute difference: " << diff << std::endl;
    if (diff < 1e-4) {
        std::cout << "PASS: scores agree within 1e-4" << std::endl;
    } else {
        std::cout << "FAIL: scores differ by more than 1e-4" << std::endl;
    }

    f->Close();
}
