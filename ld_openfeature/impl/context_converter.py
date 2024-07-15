from logging import getLogger
from typing import Any, Dict, List, Optional

from ldclient.context import Context, ContextBuilder, ContextMultiBuilder
from openfeature.evaluation_context import EvaluationContext


logger = getLogger("launchdarkly-openfeature-server")


class EvaluationContextConverter:
    def to_ld_context(self, context: EvaluationContext) -> Context:
        """
        Create an Context from an EvaluationContext.

        A context will always be created, but the created context may be
        invalid. Log messages will be written to indicate the source of the
        problem.
        """
        attributes = context.attributes

        kind = attributes.get('kind')
        if kind == "multi":
            return self.__build_multi_context(context)

        if kind is not None and not isinstance(kind, str):
            logger.warning("'kind' was set to a non-string value; defaulting to user")
            kind = 'user'

        targeting_key = context.targeting_key
        key = attributes.get('key')
        targeting_key = self.__get_targeting_key(targeting_key, key)

        kind = "user" if kind is None else kind
        return self.__build_single_context(attributes, kind, targeting_key)

    def __get_targeting_key(self, targeting_key: Optional[str], key: Any) -> str:
        # The targeting key may be set but empty. So we want to treat an empty
        # string as a not defined one. Later it could become null, so we will
        # need to check that.
        if targeting_key is not None and targeting_key != "" and isinstance(key, str):
            # There is both a targeting key and a key. It will work, but
            # probably is not intentional.
            logger.warning("EvaluationContext contained both a 'key' and 'targetingKey'.")

        if key is not None and not isinstance(key, str):
            logger.warning("A non-string 'key' attribute was provided.")

        if key is not None and isinstance(key, str):
            targeting_key = targeting_key if targeting_key else key

        if targeting_key is None or targeting_key == "" or not isinstance(targeting_key, str):
            logger.error("The EvaluationContext must contain either a 'targetingKey' or a 'key' and the type must be a string.")

        return targeting_key if targeting_key else ""

    def __build_multi_context(self, context: EvaluationContext) -> Context:
        builder = ContextMultiBuilder()

        for kind, attributes in context.attributes.items():
            if kind == 'kind':
                continue

            if not isinstance(attributes, Dict):
                logger.warning("Top level attributes in a multi-kind context should be dictionaries")
                continue

            key = attributes.get('key')
            targeting_key = attributes.get('targetingKey')

            if targeting_key is not None and not isinstance(targeting_key, str):
                continue

            targeting_key = self.__get_targeting_key(targeting_key, key)
            single_context = self.__build_single_context(attributes, kind, targeting_key)

            builder.add(single_context)

        return builder.build()

    def __build_single_context(self, attributes: Dict, kind: str, key: str) -> Context:
        builder = ContextBuilder(key)
        builder.kind(kind)

        for k, v in attributes.items():
            if k == 'key' or k == 'targetingKey' or k == 'kind':
                continue

            if k == 'name' and isinstance(v, str):
                builder.name(v)
            elif k == 'name':
                logger.error("The attribute 'name' must be a string")
            elif k == 'anonymous' and isinstance(v, bool):
                builder.anonymous(v)
            elif k == 'anonymous':
                logger.error("The attribute 'anonymous' must be a boolean")
            elif k == 'privateAttributes' and isinstance(v, list):
                private_attributes: List[str] = []
                for private_attribute in v:
                    if not isinstance(private_attribute, str):
                        logger.error("'privateAttributes' must be an array of only string values")
                        continue

                    private_attributes.append(private_attribute)

                if private_attributes:
                    builder.private(*private_attributes)
            elif k == 'privateAttributes':
                logger.error("The attribute 'privateAttributes' must be an array")
            else:
                builder.set(k, v)

        return builder.build()
