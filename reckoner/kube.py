
import sys
import logging
import traceback

from kubernetes import client, config


class NamespaceManager(object):

    def __init__(self, namespace_name, namespace_management) -> None:
        """ Manages a namespace for the chart
        Accepts:
        - namespace: Which may be a string or a dictionary
        """
        self._namespace_name = namespace_name
        self._metadata = namespace_management.get('metadata', {})
        self._overwrite = namespace_management.get(
            'settings',
            {}
        ).get(
            'overwrite',
            False
        )
        self.__load_config()

    @property
    def namespace_name(self) -> str:
        """ Name of the namespace we are managing """
        return self._namespace_name

    @property
    def namespace(self) -> str:
        """ Namespace object we are managing 
        https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Namespace.md"""
        return self._namespace

    @property
    def metadata(self) -> dict:
        """ List of metadata settings parsed from the
        from the chart and course """
        return self._metadata

    @property
    def overwrite(self) -> bool:
        """ List of metadata settings parsed from the
        from the chart and course """
        return self._overwrite

    def __load_config(self):
        """ Protected method do load kubernetes config"""
        try:
            config.load_kube_config()
            self.v1client = client.CoreV1Api()
        except Exception as e:
            logging.error('Unable to load kuberentes configuration')
            logging.debug(traceback.format_exc())
            raise e

    def create_and_manage(self):
        """ Create namespace and patch metadata """
        self._namespace = self.create()
        self.patch_metadata()

    def patch_metadata(self):
        """ Patch namepace with metadata respecting overwrite setting.
        Returns True on success
        Raises error on failure
        """
        if self.overwrite:
            patch_metadata = self.metadata
            logging.debug("Overwiting Namespace Metadata")
        else:
            annotations = {}
            for annotation_name, annotation_value in self.metadata.get('annotations').items():
                try:
                    self.namespace.metadata.annotations[annotation_name]
                except (TypeError, KeyError):
                    annotations[annotation_name] = annotation_value

            labels = {}
            for label_name, label_value in self.metadata.get('labels').items():
                try:
                    self.namespace.metadata.labels[label_name]
                except (TypeError, KeyError):
                    labels[label_name] = label_value

            patch_metadata = {'annotations': annotations, 'labels': labels}
        logging.debug("Patch Metadata: {}".format(patch_metadata))
        patch = {'metadata': patch_metadata}
        res = self.v1client.patch_namespace(self.namespace_name, patch)

    def create(self):
        """ Create a namespace in the configured kubernetes cluster if it does not already exist

        Arguments:
        None

        Returns Namespace
        Raises error in case of failure

        """
        _namespaces = [namespace for namespace in self.cluster_namespaces if namespace.metadata.name == self.namespace_name]

        if _namespaces == []:
            logging.info('Namespace {} not found. Creating it now.'.format(self.namespace_name))
            try:
                return self.v1client.create_namespace(
                    client.V1Namespace(
                        metadata=client.V1ObjectMeta(name=self.namespace_name)
                    )
                )

            except Exception as e:
                logging.error("Unable to create namespace in cluster! {}".format(e))
                logging.debug(traceback.format_exc())
                raise e
        else:
            return _namespaces[0]

    @property
    def cluster_namespaces(self) -> list:
        """ Lists namespaces in the configured kubernetes cluster.
        No arguments
        Returns list of namespace objects
        """
        try:
            namespaces = self.v1client.list_namespace()
            return [namespace for namespace in namespaces.items]
        except Exception as e:
            logging.error("Unable to get namespaces in cluster! {}".format(e))
            logging.debug(traceback.format_exc())
            raise e