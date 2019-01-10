#! /usr/bin/env python

import argparse
import sys
import matplotlib

matplotlib.use('agg')
import numpy as np

from prior_networks.uncertainty_functions import *
from prior_networks.dirichlet.dirichlet_prior_network_conv import PriorNetConv
from prior_networks.dirichlet.dirichlet_prior_network_mlp import PriorNetMLP

commandLineParser = argparse.ArgumentParser(description='Compute features from labels.')
commandLineParser.add_argument('--seed', type=int, default=100,
                               help='Specify the global random seed')
commandLineParser.add_argument('--name', type=str, default='model',
                               help='Specify the name of the model')
commandLineParser.add_argument('--debug', type=int, choices=[0, 1, 2], default=0,
                               help='Specify the name of the model')
commandLineParser.add_argument('--load_path', type=str, default='./',
                               help='Specify path to model which should be loaded')
commandLineParser.add_argument('in_domain_pattern', type=str,
                               help='which orignal data is saved should be loaded')
commandLineParser.add_argument('out_domain_pattern', type=str,
                               help='which orignal data is saved should be loaded')
commandLineParser.add_argument('output_dir', type=str,
                               help='which orignal data is saved should be loaded')
commandLineParser.add_argument('model_type',
                               choices=['MLP', 'CONV'],
                               help='which should be loaded')
commandLineParser.add_argument('--show', type=bool, default=False,
                               help='which orignal data is saved should be loaded')
commandLineParser.add_argument('--overwrite', type=bool, default=False,
                               help='which orignal data is saved should be loaded')
commandLineParser.add_argument('--least_likely', type=bool, default=False,
                               help='which orignal data is saved should be loaded')
commandLineParser.add_argument('--Log', type=bool, default=False,
                               help='which orignal data is saved should be loaded')
commandLineParser.add_argument('--noise_corruption', type=float, default=0.0,
                               help='which orignal data is saved should be loaded')


def main(argv=None):
    args = commandLineParser.parse_args()
    if not os.path.isdir('CMDs'):
        os.mkdir('CMDs')
    with open('CMDs/step_evaluate_adversarial.txt', 'a') as f:
        f.write(' '.join(sys.argv) + '\n')
        f.write('--------------------------------\n')
    if os.path.isdir(args.output_dir) and not args.overwrite:
        print 'Directory', args.output_dir, "exists. Exiting..."
        sys.exit()
    elif os.path.isdir(args.output_dir) and args.overwrite:
        for f in os.listdir(args.output_dir):
            os.remove(os.path.join(args.output_dir, f))
    else:
        os.makedirs(args.output_dir)

    if args.model_type == 'MLP':
        dpn = PriorNetMLP(network_architecture=None,
                          seed=args.seed,
                          name=args.name,
                          save_path='./',
                          fa_path=None,
                          load_path=args.load_path,
                          debug_mode=args.debug)
    elif args.model_type == 'CONV':
        dpn = PriorNetConv(network_architecture=None,
                           seed=args.seed,
                           name=args.name,
                           save_path='./',
                           fa_path=None,
                           load_path=args.load_path,
                           debug_mode=args.debug)

    in_labels, in_probs, in_logits = dpn.eval(args.in_domain_pattern,
                                              batch_size=100,
                                              n_samples=1,
                                              dropout=1.0,
                                              corruption=args.noise_corruption)
    out_labels, out_probs, out_logits = dpn.eval(args.out_domain_pattern,
                                                 batch_size=100,
                                                 n_samples=1,
                                                 dropout=1.0,
                                                 corruption=args.noise_corruption)

    sanity = np.mean(np.asarray(in_labels == out_labels, dtype=np.float32))
    assert sanity == 1.0

    in_preds = np.argmax(in_probs, axis=1)
    min_preds = np.argmin(in_probs, axis=1)
    two_best_preds = np.argsort(in_probs,axis=1)[:,-2]
    out_preds = np.argmax(out_probs, axis=1)

    if args.least_likely==True:
        flipped = np.asarray(min_preds == out_preds, dtype=np.int32)
    else:
        flipped = np.asarray(two_best_preds == out_preds, dtype=np.int32)
    success_rate = np.mean(np.asarray(flipped, dtype=np.float32))
    in_alphas = np.exp(in_logits)
    out_alphas = np.exp(out_logits)

    path = os.path.join(args.output_dir, 'successful_attacks.txt')
    np.savetxt(path, flipped)

    class_flipped = np.asarray(in_preds != out_preds, dtype=np.int32)
    path = os.path.join(args.output_dir, 'class_flipped.txt')
    np.savetxt(path, class_flipped)

    accuracy = jaccard_similarity_score(out_labels, out_preds)
    with open(os.path.join(args.output_dir, 'results.txt'), 'a') as f:
        f.write('Classification Error: ' + str(np.round(100 * (1.0 - accuracy), 1)) + '\n')
        f.write('Adversarial Success rate: ' + str(np.round(100 * success_rate, 1)) + '\n')

    print np.mean(in_logits), np.std(in_logits)
    print np.mean(out_logits), np.std(out_logits)

    # Compute Labels
    in_domain = np.ones_like(in_labels)
    out_domain = np.zeros_like(out_labels)
    domain_labels = np.concatenate((in_domain, out_domain), axis=0)

    # Calculate Uncertainties
    in_uncertainties = calculate_dirichlet_uncertainty(in_probs, in_alphas)
    out_uncertainties = calculate_dirichlet_uncertainty(out_probs, out_alphas)

    for key in in_uncertainties.keys():
        save_path = os.path.join(args.output_dir, key + '_in.txt')
        np.savetxt(save_path, in_uncertainties[key][0])
    for key in out_uncertainties.keys():
        save_path = os.path.join(args.output_dir, key + '_out.txt')
        np.savetxt(save_path, out_uncertainties[key][0])

    # Plot ROC AUC Curves and Accuracy Curves
    plot_roc_curves(domain_labels,
                    in_uncertainties,
                    out_uncertainties,
                    save_path=args.output_dir,
                    log=args.Log,
                    classes_flipped=flipped,
                    adversarial=True,
                    show=True)
    plot_uncertainties(in_uncertainties,
                       out_uncertainties,
                       save_path=args.output_dir,
                       log=args.Log,
                       show=True)

if __name__ == '__main__':
    main()
