from __future__ import annotations
from typing import Optional

from .interfaces import (
    IJobManager, ITaskRunnerFactory, IUiClientFactory, 
    IMetricsCollector, IJobRepository
)
from .services import (
    JobManager, InMemoryJobRepository, SimpleMetricsCollector, 
    DefaultUiClientFactory
)
from .factories import TaskRunnerFactory
from .orchestrator_v2 import WorkerOrchestrator


class DIContainer:
    """
    Dependency Injection Container following Dependency Inversion Principle.
    
    This container manages the creation and wiring of all dependencies,
    making the system loosely coupled and easily testable.
    """
    
    def __init__(self):
        self._instances = {}
        self._singletons = {}
    
    def register_singleton(self, interface_type: type, implementation: object) -> None:
        """Register a singleton instance."""
        self._singletons[interface_type] = implementation
    
    def register_factory(self, interface_type: type, factory_func: callable) -> None:
        """Register a factory function for creating instances."""
        self._instances[interface_type] = factory_func
    
    def get(self, interface_type: type) -> object:
        """Get instance of specified type."""
        # Check singletons first
        if interface_type in self._singletons:
            return self._singletons[interface_type]
        
        # Check factory registrations
        if interface_type in self._instances:
            return self._instances[interface_type]()
        
        # Auto-wire if not registered
        return self._auto_wire(interface_type)
    
    def _auto_wire(self, interface_type: type) -> object:
        """Auto-wire dependencies for common types."""
        if interface_type == IJobRepository:
            return InMemoryJobRepository()
        
        elif interface_type == IMetricsCollector:
            return SimpleMetricsCollector()
        
        elif interface_type == IUiClientFactory:
            return DefaultUiClientFactory()
        
        elif interface_type == ITaskRunnerFactory:
            ui_client_factory = self.get(IUiClientFactory)
            return TaskRunnerFactory(ui_client_factory)
        
        elif interface_type == IJobManager:
            repository = self.get(IJobRepository)
            metrics = self.get(IMetricsCollector)
            ui_factory = self.get(IUiClientFactory)
            return JobManager(repository, metrics, ui_factory)
        
        elif interface_type == WorkerOrchestrator:
            job_manager = self.get(IJobManager)
            task_factory = self.get(ITaskRunnerFactory)
            metrics = self.get(IMetricsCollector)
            return WorkerOrchestrator(job_manager, task_factory, metrics)
        
        else:
            raise ValueError(f"Cannot auto-wire type: {interface_type}")


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get global container instance."""
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


def configure_container() -> DIContainer:
    """Configure the dependency injection container with default implementations."""
    container = get_container()
    
    # Register singleton instances if needed
    # container.register_singleton(IJobRepository, custom_repository)
    
    # Register factory functions if needed
    # container.register_factory(IMetricsCollector, lambda: CustomMetricsCollector())
    
    return container


def reset_container() -> None:
    """Reset container - useful for testing."""
    global _container
    _container = None


# Convenience functions for getting common services
def get_orchestrator() -> WorkerOrchestrator:
    """Get configured orchestrator instance."""
    return get_container().get(WorkerOrchestrator)


def get_job_manager() -> IJobManager:
    """Get job manager instance."""
    return get_container().get(IJobManager)


def get_task_runner_factory() -> ITaskRunnerFactory:
    """Get task runner factory instance."""
    return get_container().get(ITaskRunnerFactory)


def get_metrics_collector() -> IMetricsCollector:
    """Get metrics collector instance."""
    return get_container().get(IMetricsCollector)