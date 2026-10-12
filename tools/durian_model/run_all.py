"""Run the seven explicit VS Code steps in order."""
from importlib import import_module

STEPS = ['step0_audit_data', 'step1_split_years', 'step2_process_data', 'step3_train_model',
         'step4_investigate_feature_importance', 'step5_evaluate_result', 'step6_predict_live']


def main():
    for name in STEPS:
        import_module(name).run()


if __name__ == '__main__':
    main()
