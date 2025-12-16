"""
Evaluation script for the Learning Roadmap Generator system.
This script performs comprehensive evaluation of the recommendation engine
and overall system performance.
"""

import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, ndcg_score, mean_absolute_error
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set style for plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")


class RecommendationEvaluator:
    """Evaluates the performance of the recommendation system."""

    def __init__(self, recommendation_engine):
        self.engine = recommendation_engine

    def evaluate_recommendations(
        self,
        test_users: List[int],
        test_interactions: List[Dict],
        all_resources_df: pd.DataFrame,
        k_values: List[int] = [5, 10, 15, 20]
    ) -> Dict:
        """
        Evaluate recommendation quality using standard metrics.

        Args:
            test_users: List of user IDs for testing
            test_interactions: List of user-resource interactions
            all_resources_df: DataFrame with all available resources
            k_values: Values of k for evaluation metrics

        Returns:
            Dictionary with evaluation metrics
        """
        logger.info(f"Evaluating recommendations for {len(test_users)} users...")

        results = {
            'precision': {},
            'recall': {},
            'ndcg': {},
            'coverage': 0,
            'diversity': 0,
            'novelty': 0,
            'response_time': 0
        }

        all_predictions = []
        all_actuals = []
        response_times = []

        for user_id in test_users[:50]:  # Limit for evaluation speed
            # Get user data (simplified)
            user_data = {'learning_style': 'visual', 'experience_level': 'beginner'}

            # Get user's actual interactions
            user_actual_interactions = [
                interaction for interaction in test_interactions
                if interaction.get('user_id') == user_id
            ]

            # Get user's test interactions (simulated held-out)
            user_test_interactions = user_actual_interactions[:len(user_actual_interactions)//2]

            # Start timing
            start_time = time.time()

            # Generate recommendations
            recommendations = self.engine.get_recommendations(
                user_id=user_id,
                user_data=user_data,
                user_interactions=user_test_interactions,
                resources_df=all_resources_df,
                limit=max(k_values)
            )

            # End timing
            response_time = time.time() - start_time
            response_times.append(response_time)

            # Get actual relevant items (items user interacted with in test set)
            actual_relevant = set()
            for interaction in user_actual_interactions[len(user_actual_interactions)//2:]:
                if interaction.get('interaction_type') in ['complete', 'rate', 'save']:
                    actual_relevant.add(interaction['resource_id'])

            # Get predicted items
            predicted_items = [rec['id'] for rec in recommendations]

            # Create binary relevance vectors for different k values
            for k in k_values:
                pred_k = predicted_items[:k]
                actual_binary = [1 if item in actual_relevant else 0 for item in pred_k]

                # Pad predictions to length k
                while len(pred_k) < k:
                    pred_k.append(0)  # Assuming 0 is not a valid resource ID

                pred_binary = [1] * min(k, len(predicted_items)) + [0] * max(0, k - len(predicted_items))

                all_predictions.append(pred_binary)
                all_actuals.append(actual_binary)

                # Calculate NDCG
                if actual_relevant:
                    ndcg_val = ndcg_score([actual_binary], [pred_binary], k=k)
                    if k not in results['ndcg']:
                        results['ndcg'][k] = []
                    results['ndcg'][k].append(ndcg_val)

        # Calculate aggregate metrics
        for k in k_values:
            pred_k = [pred[:k] for pred in all_predictions]
            actual_k = [act[:k] for act in all_actuals]

            try:
                precision = np.mean([precision_score(act, pred, zero_division=0) for act, pred in zip(actual_k, pred_k)])
                recall = np.mean([recall_score(act, pred, zero_division=0) for act, pred in zip(actual_k, pred_k)])

                results['precision'][k] = precision
                results['recall'][k] = recall
            except:
                results['precision'][k] = 0.0
                results['recall'][k] = 0.0

            if k in results['ndcg']:
                results['ndcg'][k] = np.mean(results['ndcg'][k])

        # Calculate other metrics
        results['response_time'] = np.mean(response_times)

        # Calculate coverage (percentage of items recommended)
        all_recommended_items = set()
        for recs in [self.engine.get_recommendations(uid, {'learning_style': 'visual'}, [], all_resources_df, 10)
                     for uid in test_users[:10]]:
            all_recommended_items.update(rec['id'] for rec in recs)

        results['coverage'] = len(all_recommended_items) / len(all_resources_df) if len(all_resources_df) > 0 else 0

        logger.info(f"Evaluation completed. Coverage: {results['coverage']:.3f}, Avg response time: {results['response_time']:.3f}s")

        return results

    def evaluate_user_satisfaction(self, user_interactions: List[Dict]) -> Dict:
        """
        Evaluate user satisfaction metrics from interaction data.

        Args:
            user_interactions: List of user-resource interactions

        Returns:
            Dictionary with satisfaction metrics
        """
        logger.info("Evaluating user satisfaction...")

        df = pd.DataFrame(user_interactions)

        metrics = {}

        # Completion rate
        if 'interaction_type' in df.columns:
            completion_rate = (df['interaction_type'] == 'complete').mean()
            metrics['completion_rate'] = completion_rate

        # Average rating
        if 'rating' in df.columns:
            avg_rating = df['rating'].dropna().mean()
            metrics['average_rating'] = avg_rating

        # Engagement metrics
        if 'time_spent_minutes' in df.columns:
            avg_time_spent = df['time_spent_minutes'].dropna().mean()
            metrics['average_time_spent'] = avg_time_spent

        # Interaction diversity
        if 'resource_id' in df.columns:
            unique_resources = df['resource_id'].nunique()
            total_interactions = len(df)
            metrics['interaction_diversity'] = unique_resources / total_interactions if total_interactions > 0 else 0

        # User retention (users with multiple interactions)
        if 'user_id' in df.columns:
            user_interaction_counts = df.groupby('user_id').size()
            retention_rate = (user_interaction_counts > 1).mean()
            metrics['user_retention'] = retention_rate

        return metrics

    def generate_evaluation_report(self, results: Dict, user_satisfaction: Dict) -> str:
        """Generate a comprehensive evaluation report."""

        report = []
        report.append("=" * 60)
        report.append("LEARNING ROADMAP GENERATOR - EVALUATION REPORT")
        report.append("=" * 60)

        report.append("\n📊 RECOMMENDATION QUALITY METRICS")
        report.append("-" * 40)

        for metric_name, values in results.items():
            if isinstance(values, dict):
                report.append(f"\n{metric_name.upper()}:")
                for k, value in values.items():
                    report.append(f"  @{k:2d}: {value:.4f}")
            else:
                report.append(f"{metric_name.upper()}: {values}")

        report.append("\n😊 USER SATISFACTION METRICS")
        report.append("-" * 40)

        satisfaction_descriptions = {
            'completion_rate': 'Completion Rate',
            'average_rating': 'Average Rating',
            'average_time_spent': 'Avg Time Spent (minutes)',
            'interaction_diversity': 'Interaction Diversity',
            'user_retention': 'User Retention Rate'
        }

        for metric, value in user_satisfaction.items():
            description = satisfaction_descriptions.get(metric, metric.replace('_', ' ').title())
            if pd.notna(value):
                if 'rate' in metric:
                    report.append(f"{description}: {value:.1%}")
                elif 'time' in metric:
                    report.append(f"{description}: {value:.1f}")
                else:
                    report.append(f"{description}: {value:.3f}")
            else:
                report.append(f"{description}: N/A")

        report.append("\n🎯 SYSTEM PERFORMANCE")
        report.append("-" * 40)
        report.append(f"Average Response Time: {results.get('response_time', 0):.3f} seconds")
        report.append(f"Coverage: {results.get('coverage', 0):.1%}")

        # Performance interpretation
        report.append("\n💡 INTERPRETATION")
        report.append("-" * 40)

        precision = results.get('precision', {}).get(10, 0)
        if precision > 0.1:
            report.append("✅ Good recommendation precision - users find relevant content")
        elif precision > 0.05:
            report.append("⚠️ Moderate recommendation precision - some tuning needed")
        else:
            report.append("❌ Low recommendation precision - significant improvements needed")

        coverage = results.get('coverage', 0)
        if coverage > 0.5:
            report.append("✅ Good content coverage - diverse recommendations")
        elif coverage > 0.2:
            report.append("⚠️ Moderate content coverage - could be more diverse")
        else:
            report.append("❌ Low content coverage - limited recommendation variety")

        response_time = results.get('response_time', 0)
        if response_time < 0.5:
            report.append("✅ Fast response times - good user experience")
        elif response_time < 2.0:
            report.append("⚠️ Acceptable response times - could be optimized")
        else:
            report.append("❌ Slow response times - performance optimization needed")

        return "\n".join(report)

    def plot_evaluation_results(self, results: Dict, save_path: str = None):
        """Generate evaluation plots."""

        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('Recommendation System Evaluation Results', fontsize=16)

        # Precision-Recall plot
        k_values = list(results['precision'].keys())
        precision_vals = [results['precision'][k] for k in k_values]
        recall_vals = [results['recall'][k] for k in k_values]

        axes[0, 0].plot(k_values, precision_vals, 'o-', label='Precision', color='blue')
        axes[0, 0].plot(k_values, recall_vals, 's-', label='Recall', color='green')
        axes[0, 0].set_xlabel('k (Number of Recommendations)')
        axes[0, 0].set_ylabel('Score')
        axes[0, 0].set_title('Precision and Recall @ k')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # NDCG plot
        if 'ndcg' in results and results['ndcg']:
            ndcg_vals = [results['ndcg'][k] for k in k_values]
            axes[0, 1].plot(k_values, ndcg_vals, '^-', color='red')
            axes[0, 1].set_xlabel('k (Number of Recommendations)')
            axes[0, 1].set_ylabel('NDCG Score')
            axes[0, 1].set_title('NDCG @ k')
            axes[0, 1].grid(True, alpha=0.3)

        # Coverage and Response Time
        metrics = ['coverage', 'response_time']
        values = [results.get(m, 0) for m in metrics]
        labels = ['Coverage', 'Avg Response Time (s)']

        bars = axes[1, 0].bar(labels, values, color=['skyblue', 'lightcoral'])
        axes[1, 0].set_ylabel('Value')
        axes[1, 0].set_title('System Performance Metrics')

        # Add value labels on bars
        for bar, value in zip(bars, values):
            axes[1, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                          f'{value:.3f}', ha='center', va='bottom')

        # Placeholder for future metrics
        axes[1, 1].text(0.5, 0.5, 'Future Metrics\n(Diversity, Novelty)',
                       transform=axes[1, 1].transAxes, ha='center', va='center',
                       fontsize=12, alpha=0.7)
        axes[1, 1].set_title('Additional Metrics (Coming Soon)')
        axes[1, 1].set_xlim(0, 1)
        axes[1, 1].set_ylim(0, 1)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Evaluation plots saved to {save_path}")
        else:
            plt.show()


def run_system_evaluation():
    """Run comprehensive system evaluation."""

    logger.info("Starting comprehensive system evaluation...")

    # This would typically load real data from the database
    # For demonstration, we'll create synthetic data

    # Generate synthetic user interaction data
    np.random.seed(42)
    n_users = 100
    n_resources = 500
    n_interactions = 2000

    # Generate synthetic interactions
    user_ids = np.random.randint(1, n_users + 1, n_interactions)
    resource_ids = np.random.randint(1, n_resources + 1, n_interactions)
    interaction_types = np.random.choice(['view', 'rate', 'complete', 'save'],
                                       n_interactions, p=[0.5, 0.2, 0.2, 0.1])
    ratings = np.random.choice([None, 3, 4, 5], n_interactions, p=[0.7, 0.1, 0.1, 0.1])
    time_spent = np.random.exponential(30, n_interactions)

    synthetic_interactions = []
    for i in range(n_interactions):
        interaction = {
            'user_id': int(user_ids[i]),
            'resource_id': int(resource_ids[i]),
            'interaction_type': interaction_types[i],
            'rating': ratings[i],
            'time_spent_minutes': int(time_spent[i]),
            'created_at': pd.Timestamp.now() - pd.Timedelta(days=np.random.randint(0, 30))
        }
        synthetic_interactions.append(interaction)

    # Generate synthetic resource data
    resource_data = []
    for i in range(1, n_resources + 1):
        resource = {
            'id': i,
            'title': f'Learning Resource {i}',
            'description': f'Description for resource {i}',
            'url': f'https://example.com/resource/{i}',
            'media_type': np.random.choice(['video', 'course', 'article', 'book']),
            'difficulty': np.random.choice(['beginner', 'intermediate', 'advanced']),
            'duration_minutes': np.random.randint(30, 480),
            'rating': np.random.uniform(3.0, 5.0),
            'rating_count': np.random.randint(1, 1000),
            'tags': np.random.choice(['python', 'javascript', 'data-science', 'machine-learning', 'web-development'],
                                   np.random.randint(1, 4), replace=False).tolist(),
            'prerequisites': np.random.choice(['basic-programming', 'math', 'none'],
                                            np.random.randint(0, 3), replace=False).tolist(),
            'learning_style': np.random.choice(['visual', 'auditory', 'kinesthetic']),
            'source': np.random.choice(['coursera', 'udemy', 'youtube', 'edx'])
        }
        resource_data.append(resource)

    resources_df = pd.DataFrame(resource_data)

    # Initialize evaluator with the recommendation engine
    from app.core.recommendation_engine import recommendation_engine
    evaluator = RecommendationEvaluator(recommendation_engine)

    # Run evaluation
    test_users = list(range(1, min(21, n_users + 1)))  # Test first 20 users

    logger.info("Running recommendation quality evaluation...")
    results = evaluator.evaluate_recommendations(test_users, synthetic_interactions, resources_df)

    logger.info("Evaluating user satisfaction...")
    user_satisfaction = evaluator.evaluate_user_satisfaction(synthetic_interactions)

    # Generate report
    report = evaluator.generate_evaluation_report(results, user_satisfaction)
    print(report)

    # Generate plots
    try:
        evaluator.plot_evaluation_results(results, save_path='evaluation_results.png')
    except ImportError:
        logger.warning("Matplotlib not available for plotting")

    return results, user_satisfaction


if __name__ == "__main__":
    # Run evaluation
    results, satisfaction = run_system_evaluation()

    # Save results to file
    with open('evaluation_report.txt', 'w') as f:
        from datetime import datetime
        f.write(f"Evaluation Report - {datetime.now()}\n\n")
        f.write("Recommendation Results:\n")
        for key, value in results.items():
            f.write(f"{key}: {value}\n")
        f.write("\nUser Satisfaction:\n")
        for key, value in satisfaction.items():
            f.write(f"{key}: {value}\n")

    logger.info("Evaluation completed. Results saved to evaluation_report.txt")