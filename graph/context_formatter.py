class ContextFormatter:
    """
    Formats GraphRetriever output into clean LLM context.

    Current GraphRetriever structure:

    record = {
        "policy_id": ...,
        "policy": ...,
        "loan": ...,
        "section_id": ...,
        "section": ...,
        "content": ...,
        "category": ...,
        "entities": [
            {
                "relationship": ...,
                "labels": [...],
                "properties": {...}
            }
        ]
    }
    """

    # ==========================================================
    # FORMAT CONTEXT
    # ==========================================================

    def format_context(self, raw_context):
        """
        Convert retrieved Neo4j records into LLM-ready context.
        """

        if not raw_context:
            return ""

        context_parts = []

        grouped = {}

        # ------------------------------------------------------
        # GROUP BY POLICY + SECTION
        # ------------------------------------------------------

        for record in raw_context:

            policy = (
                record.get("policy")
                or "Unknown Policy"
            )

            section = (
                record.get("section")
                or "Unknown Section"
            )

            if policy not in grouped:
                grouped[policy] = {}

            if section not in grouped[policy]:
                grouped[policy][section] = []

            grouped[policy][section].append(record)

        # ------------------------------------------------------
        # BUILD CONTEXT
        # ------------------------------------------------------

        for policy, sections in grouped.items():

            context_parts.append(
                f"### Policy: {policy}"
            )

            for section, records in sections.items():

                context_parts.append(
                    f"\nSECTION: {section}"
                )

                content_seen = set()
                fact_seen = set()

                graph_facts_added = False

                # --------------------------------------------------
                # RECORDS
                # --------------------------------------------------

                for record in records:

                    # ==================================================
                    # SECTION CONTENT
                    # ==================================================

                    content = (
                        record.get("content")
                        or ""
                    ).strip()

                    if (
                        content
                        and content not in content_seen
                    ):

                        content_seen.add(content)

                        context_parts.append(
                            content
                        )

                    # ==================================================
                    # CATEGORY
                    # ==================================================

                    category = (
                        record.get("category")
                        or ""
                    ).strip()

                    if category:

                        category_text = (
                            f"Category: {category}"
                        )

                        if category_text not in content_seen:

                            content_seen.add(
                                category_text
                            )

                            context_parts.append(
                                category_text
                            )

                    # ==================================================
                    # GRAPH ENTITIES
                    # ==================================================

                    entities = (
                        record.get("entities")
                        or []
                    )

                    for entity in entities:

                        relationship = (
                            entity.get(
                                "relationship"
                            )
                        )

                        labels = (
                            entity.get("labels")
                            or []
                        )

                        properties = (
                            entity.get("properties")
                            or {}
                        )

                        if not relationship:
                            continue

                        # ----------------------------------------------
                        # LABELS
                        # ----------------------------------------------

                        labels_text = (
                            ", ".join(labels)
                            if labels
                            else "Entity"
                        )

                        # ----------------------------------------------
                        # PROPERTIES
                        # ----------------------------------------------

                        properties_text = ", ".join(
                            f"{key}: {value}"
                            for key, value
                            in sorted(
                                properties.items()
                            )
                        )

                        fact = (
                            f"{relationship} "
                            f"-> {labels_text} "
                            f"({properties_text})"
                        )

                        if fact in fact_seen:
                            continue

                        fact_seen.add(fact)

                        # ----------------------------------------------
                        # GRAPH FACT HEADING
                        # ----------------------------------------------

                        if not graph_facts_added:

                            context_parts.append(
                                "\nRELATED GRAPH FACTS:"
                            )

                            graph_facts_added = True

                        # ----------------------------------------------
                        # ADD FACT
                        # ----------------------------------------------

                        context_parts.append(
                            "- " + fact
                        )

            # ------------------------------------------------------
            # POLICY SEPARATOR
            # ------------------------------------------------------

            context_parts.append(
                "\n" + "-" * 50
            )

        return "\n".join(
            context_parts
        ).strip()

    # ==========================================================
    # BACKWARD COMPATIBILITY
    # ==========================================================

    def format(self, raw_context):
        """
        Alias for format_context().

        Keeps compatibility with older GraphRAG code.
        """

        return self.format_context(
            raw_context
        )

    # ==========================================================
    # EXTRACT STATISTICS
    # ==========================================================

    def extract_statistics(self, raw_context):
        """
        Extract retrieval statistics.

        Returns:
            policies
            section_count
            relationship_count
        """

        if not raw_context:

            return {
                "policies": [],
                "section_count": 0,
                "relationship_count": 0
            }

        # ------------------------------------------------------
        # POLICIES
        # ------------------------------------------------------

        policies = sorted({
            record.get("policy")
            for record in raw_context
            if record.get("policy")
        })

        # ------------------------------------------------------
        # UNIQUE POLICY + SECTION COMBINATIONS
        # ------------------------------------------------------

        sections = set()

        for record in raw_context:

            policy = record.get(
                "policy"
            )

            section = record.get(
                "section"
            )

            if section:

                sections.add(
                    (
                        policy,
                        section
                    )
                )

        # ------------------------------------------------------
        # RELATIONSHIP COUNT
        # ------------------------------------------------------

        relationship_count = 0

        seen_relationships = set()

        for record in raw_context:

            entities = (
                record.get("entities")
                or []
            )

            for entity in entities:

                relationship = (
                    entity.get(
                        "relationship"
                    )
                )

                properties = (
                    entity.get(
                        "properties"
                    )
                    or {}
                )

                if not relationship:
                    continue

                # Avoid counting exact duplicate graph facts
                relationship_key = (
                    record.get("policy_id"),
                    record.get("section_id"),
                    relationship,
                    tuple(
                        sorted(
                            properties.items()
                        )
                    )
                )

                if relationship_key not in seen_relationships:

                    seen_relationships.add(
                        relationship_key
                    )

                    relationship_count += 1

        return {
            "policies": policies,

            "section_count":
                len(sections),

            "relationship_count":
                relationship_count
        }

    # ==========================================================
    # GROUP BY POLICY
    # ==========================================================

    def group_by_policy(self, raw_context):
        """
        Group retrieved records by policy and section.

        Used by GraphRAG fallback responses.
        """

        policies_seen = {}

        if not raw_context:
            return policies_seen

        for record in raw_context:

            policy_name = (
                record.get("policy")
                or "Unknown Policy"
            )

            section_name = (
                record.get("section")
                or "Unknown Section"
            )

            content = (
                record.get("content")
                or ""
            ).strip()

            # --------------------------------------------------
            # POLICY
            # --------------------------------------------------

            if policy_name not in policies_seen:

                policies_seen[
                    policy_name
                ] = {}

            # --------------------------------------------------
            # SECTION
            # --------------------------------------------------

            if section_name not in policies_seen[
                policy_name
            ]:

                policies_seen[
                    policy_name
                ][
                    section_name
                ] = []

            # --------------------------------------------------
            # CONTENT
            # --------------------------------------------------

            if content:

                if content not in policies_seen[
                    policy_name
                ][
                    section_name
                ]:

                    policies_seen[
                        policy_name
                    ][
                        section_name
                    ].append(
                        content
                    )

        return policies_seen

    # ==========================================================
    # EXTRACT KEYWORDS
    # ==========================================================

    def extract_keywords(
        self,
        question,
        retriever=None
    ):
        """
        Reuse GraphRetriever's existing keyword detection.

        This prevents duplicate keyword logic.
        """

        if retriever is not None:

            try:

                return retriever.extract_keywords(
                    question
                )

            except Exception:

                pass

        return []

    # ==========================================================
    # FORMAT GRAPH ENTITIES ONLY
    # ==========================================================

    def format_entities(self, raw_context):
        """
        Return only structured graph facts.
        """

        if not raw_context:
            return []

        facts = []

        seen = set()

        for record in raw_context:

            policy = record.get(
                "policy",
                "Unknown Policy"
            )

            section = record.get(
                "section",
                "Unknown Section"
            )

            entities = (
                record.get("entities")
                or []
            )

            for entity in entities:

                relationship = (
                    entity.get(
                        "relationship"
                    )
                )

                labels = (
                    entity.get("labels")
                    or []
                )

                properties = (
                    entity.get("properties")
                    or {}
                )

                if not relationship:
                    continue

                labels_text = (
                    ", ".join(labels)
                    if labels
                    else "Entity"
                )

                properties_text = ", ".join(
                    f"{key}: {value}"
                    for key, value
                    in sorted(
                        properties.items()
                    )
                )

                fact = (
                    f"{policy} | "
                    f"{section} | "
                    f"{relationship} -> "
                    f"{labels_text} | "
                    f"{properties_text}"
                )

                if fact in seen:
                    continue

                seen.add(fact)

                facts.append(
                    fact
                )

        return facts